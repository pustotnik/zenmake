# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

__all__ = [
    'top',
    'out',
    'options',
    'init',
    'configure',
    'build',
    'distclean',
    'shutdown',
    'APPNAME',
    'VERSION',
]

import os

from waflib.Build import BuildContext, CFG_FILES
from zm.pyutils import viewitems, viewvalues
from zm.constants import WAF_CACHE_DIRNAME, CONFTEST_DIR_PREFIX
from zm import cli, error, log
from zm.buildconf.scheme import KNOWN_TASK_PARAM_NAMES
from zm.waf import assist

joinpath = os.path.join
abspath = os.path.abspath
normpath = os.path.normpath

# These variables are set in another place.
# To detect possible errors these variables are set to 0, not to None.
top = 0
out = 0

APPNAME = None
VERSION = None

def options(_):
    """
    Implementation for wscript.options
    It's called by Waf as method where cmdline options can be added/removed
    """

    # This method is called before all other methods including 'init'

def init(ctx):
    """
    Implementation of wscript.init
    It's called before all other commands but after 'options'
    """

    cliArgs = cli.selected.args
    if 'buildtype' not in cliArgs:
        return

    # Next code only for command with 'buildtype' param

    bconf = ctx.getbconf()
    assert id(ctx.bconfManager.root) == id(bconf)
    buildtype = bconf.selectedBuildType

    setattr(BuildContext, 'variant', buildtype)

    assist.printZenMakeHeader(ctx.bconfManager)

def _configure(conf, bconf):

    # set context path
    conf.path = conf.getPathNode(bconf.confdir)

    buildtype = bconf.selectedBuildType
    tasks = bconf.tasks

    for taskParams in viewvalues(tasks):
        # configure all possible task params
        conf.configureTaskParams(bconf, taskParams)

    # run conf checkers
    conf.runConfTests(buildtype, tasks)

    # save envs
    for taskParams in viewvalues(tasks):

        # It's not needed anymore.
        taskParams.pop('conftests', None)

        taskVariant = taskParams['$task.variant']
        conf.setenv(taskVariant)

        # set task env variables
        # NOTICE: if set these env vars (-O2, -shared, etc) before
        # running of conf tests then the vars will affect builds in the conf tests.
        assist.setTaskEnvVars(conf.env, taskParams, bconf.customToolchains)

    # switch current env to the root env
    conf.setenv('')

    conf.addExtraMonitFiles(bconf)

def configure(conf):
    """
    Implementation of wscript.configure
    """

    configs = conf.bconfManager.configs
    for bconf in configs:
        _configure(conf, bconf)

def _setupClean(bld, bconfPaths):

    preserveFiles = []
    for env in bld.all_envs.values():
        preserveFiles.extend(bld.root.make_node(f) for f in env[CFG_FILES])
    preserveFiles.append(bld.root.make_node(bconfPaths.zmmetafile))

    excludes = '.lock* config.log'
    excludes += ' %s*/** %s/*' % (CONFTEST_DIR_PREFIX, WAF_CACHE_DIRNAME)
    removeFiles = set(bld.bldnode.ant_glob('**/*', excl = excludes, quiet = True))
    removeFiles.difference_update(preserveFiles)

    bld.clean_files = list(removeFiles)

def build(bld):
    """
    Implementation of wscript.build
    """

    buildtype = bld.validateVariant()

    bconf = bld.bconfManager.root
    assert id(bconf) == id(bld.getbconf())
    bconfPaths = bconf.confPaths

    isInstall = bld.cmd in ('install', 'uninstall')
    if isInstall:
        assist.applyInstallPaths(bld.env, cli.selected)
    elif bld.cmd == 'clean':
        _setupClean(bld, bconfPaths)
        # no need to make build tasks
        return

    # Some comments just to remember some details.
    # - ctx.path represents the path to the wscript file being executed
    # - ctx.root is the root of the file system or the folder containing
    #   the drive letters (win32 systems)
    #
    # The build context provides two additional nodes:
    #   srcnode: node representing the top-level directory (== top)
    #   bldnode: node representing the build directory     (== out)
    # To obtain a build node from a src node and vice-versa, the following methods may be used:
    #   Node.get_src()
    #   Node.get_bld()
    # top == bld.srcnode.abspath()
    # out == bld.bldnode.abspath()

    bldPathNode = bld.path

    # tasks from bconf cannot be used here
    tasks = bld.zmtasks

    allowedTasks = cli.selected.args.tasks
    if allowedTasks:
        allowedTasks = set(assist.getTaskNamesWithDeps(tasks, allowedTasks))

    for taskName, taskParams in viewitems(tasks):

        if allowedTasks and taskName not in allowedTasks:
            continue

        # set bld.path to startdir of the buildconf from which the current task
        bld.path = bld.getStartDirNode(taskParams['$startdir'])

        # task env variables are stored in separative env
        # so it's needed to switch in
        bld.variant = taskParams.get('$task.variant')

        assist.convertTaskParamNamesForWaf(taskParams)

        if 'includes' in taskParams:
            # Add the build directory path.
            # It's needed to use config header with 'conftests'.
            taskParams['includes'].append(bld.bldnode.abspath())

        if 'source' in taskParams:
            source = assist.handleTaskSourceParam(bld, taskParams['source'])
            if not source:
                msg = "No source files found for task %r." % taskName
                msg += " Nothing to build. Check config(s) and/or file(s)."
                raise error.ZenMakeError(msg)

            taskParams['source'] = source

        assist.checkWafTasksForFeatures(taskParams)

        bldParams = taskParams.copy()
        # Remove params that can conflict with waf in theory
        dropKeys = set(KNOWN_TASK_PARAM_NAMES) - assist.getUsedWafTaskKeys()
        bldParamKeys = tuple(bldParams.keys())
        dropKeys.update([k for k in bldParamKeys if k[0] == '$' ])
        dropKeys = tuple(dropKeys)
        for k in dropKeys:
            bldParams.pop(k, None)

        #special param
        bldParams['zm-task-params'] = taskParams

        # create build task generator
        bld(**bldParams)

    # just in case
    bld.path = bldPathNode

    # It's neccesary to return to original variant otherwise WAF won't find
    # correct path at the end of the building step.
    bld.variant = buildtype

def test(_):
    """
    It is special stub for the case when a project has no tests but
    user has called the command 'test'.
    This function is not called if module for the feature 'test' is loaded.
    """

    log.warn("There are no tests to build and run")

def distclean(ctx):
    """
    Implementation of wscript.distclean
    """

    bconfPaths = ctx.getbconf().confPaths
    assist.distclean(bconfPaths)

def shutdown(_):
    """
    Implementation of wscript.shutdown
    """

    # Do nothing
