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

from waflib.Build import BuildContext
from zm.constants import WAF_CACHE_DIRNAME, WAF_CFG_FILES_ENV_KEY
from zm.constants import WAF_CONFIG_LOG, CONFTEST_DIR_PREFIX
from zm import utils, cli, error, log
from zm.buildconf.scheme import KNOWN_TASK_PARAM_NAMES
from zm.waf import assist

joinpath = os.path.join
abspath = os.path.abspath
realpath = os.path.realpath
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

    bconf = ctx.bconfManager.root
    buildtype = bconf.selectedBuildType

    setattr(BuildContext, 'variant', buildtype)

    assist.printZenMakeHeader(ctx.bconfManager)

def configure(conf):
    """
    Implementation of wscript.configure
    """

    # handle such task params as includes, libpath, etc.
    conf.configureTaskParams()

    # run conf actions
    conf.runConfigActions()

    # save envs
    for taskParams in conf.allOrderedTasks:

        bconf = taskParams['$bconf']

        # It's not needed anymore.
        taskParams.pop('configure', None)

        # switch env
        conf.variant = taskParams['$task.variant']
        taskEnv = conf.env

        # it must be made after conf actions
        assist.fixToolchainEnvVars(taskEnv, taskParams)

        # set task env variables
        # NOTICE: if these env vars (-O2, -shared, etc) are set before
        # running of conf tests then the vars will affect builds in the conf tests.
        toolchainSettings = conf.getToolchainSettings(bconf.path)
        assist.setTaskEnvVars(taskEnv, taskParams, toolchainSettings)

    # switch current env to the root env
    conf.setenv('')

    for bconf in conf.bconfManager.configs:
        conf.addExtraMonitFiles(bconf)

def _setupClean(bld, bconfPaths):

    preserveFiles = []
    envKey = WAF_CFG_FILES_ENV_KEY
    for env in bld.all_envs.values():
        preserveFiles.extend(x for x in env[envKey])
    preserveFiles.append(bconfPaths.zmmetafile)
    preserveFiles = [bld.root.make_node(realpath(x)) for x in preserveFiles]

    btypeDir = realpath(bld.bconfManager.root.selectedBuildTypeDir)
    btypeNode = bld.root.make_node(btypeDir)

    excludes = WAF_CONFIG_LOG
    excludes += ' %s*/** %s/*' % (CONFTEST_DIR_PREFIX, WAF_CACHE_DIRNAME)
    removeFiles = set(btypeNode.ant_glob('**/*', excl = excludes, quiet = True))
    removeFiles.difference_update(preserveFiles)

    bld.clean_files = list(removeFiles)

def _getAllowedBuildTaskNames(allTasks):

    allowedTasks = cli.selected.args.tasks
    if not allowedTasks:
        return allowedTasks

    allTaskNames = set(allTasks.keys())
    if not set(allowedTasks).issubset(allTaskNames):
        unknownTasks = list(set(allowedTasks) - allTaskNames)
        if len(unknownTasks) == 1:
            msg = "Unknown task name %r" % unknownTasks[0]
        else:
            msg = "Unknown task names: %s" % str(unknownTasks)[1:-1]
        raise error.ZenMakeError(msg)

    allowedTasks = set(assist.getTaskNamesWithDeps(allTasks, allowedTasks))
    return allowedTasks

def build(bld):
    """
    Implementation of wscript.build
    """

    buildtype = bld.validateVariant()
    rootbconf = bld.bconfManager.root

    isInstallUninstall = bld.cmd in ('install', 'uninstall')
    if isInstallUninstall:
        # I think it's not necessery here but it doesn't make any problems
        utils.setEnvInstallDirPaths(bld.env, cli.selected.args)
    elif bld.cmd == 'clean':
        _setupClean(bld, rootbconf.confPaths)
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
    # top == bld.srcnode.abspath()
    # out == bld.bldnode.abspath()

    bldPathNode = bld.path
    btypeDir = rootbconf.selectedBuildTypeDir

    # tasks from bconf cannot be used here
    tasks = bld.zmtasks
    taskNames = bld.zmOrderedTaskNames

    allowedTasks = _getAllowedBuildTaskNames(tasks)
    if allowedTasks:
        taskNames = [x for x in taskNames if x in allowedTasks]

    for taskName in taskNames:

        taskParams = tasks[taskName]

        # set bld.path to startdir of the buildconf from which the current task
        bld.path = bld.getStartDirNode(taskParams['$startdir'])

        # task env variables are stored in separative env
        # so it's needed to switch in
        bld.variant = taskParams.get('$task.variant')

        if isInstallUninstall:
            # env of a build task doesn't have parents and we need to apply
            # install path vars to each task env
            utils.setEnvInstallDirPaths(bld.env, cli.selected.args)

        assist.convertTaskParamNamesForWaf(taskParams)

        if 'includes' in taskParams:
            # Add the build directory path.
            # It's needed to use config header with 'configure'.
            taskParams['includes'].append(btypeDir)

        if 'source' in taskParams:
            source = assist.handleTaskSourceParam(bld, taskParams)
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

        # don't make empty group for last task
        if taskParams.get('group-dependent-tasks', False) and taskName != taskNames[-1]:
            bld.add_group()

    if isInstallUninstall:
        # Make all install tasks in last build group to avoid some problems
        for taskName in taskNames:
            bld.setUpInstallFiles(tasks[taskName])

    # just in case
    bld.path = bldPathNode

    # It's neccesary to return to original variant otherwise WAF won't find
    # correct path at the end of the building step (see BuildContext.variant_dir).
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

    bconfPaths = ctx.bconfManager.root.confPaths
    assist.distclean(bconfPaths)

cleanall = distclean

def shutdown(_):
    """
    Implementation of wscript.shutdown
    """

    # Do nothing
