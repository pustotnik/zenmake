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

from waflib.ConfigSet import ConfigSet
from waflib.Build import BuildContext
from zm.pyutils import viewitems
from zm.utils import toList
from zm import cli, error, log
from zm.waf import assist
from zm.buildconf.scheme import KNOWN_TASK_PARAM_NAMES

joinpath = os.path.join
abspath = os.path.abspath

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
    Implementation for wscript.init
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

def configure(conf):
    """
    Implementation for wscript.configure
    """

    bconf = conf.getbconf()
    tasks = bconf.tasks

    if not bconf.parent: # for top-level conf only
        # set/fix vars PREFIX, BINDIR, LIBDIR
        assist.applyInstallPaths(conf.env, cli.selected)

    emptyEnv = ConfigSet()

    # load all toolchains envs
    toolchainsEnvs = conf.loadToolchains(bconf, emptyEnv)

    zmcachedir = bconf.confPaths.zmcachedir
    buildtype = bconf.selectedBuildType

    # Prepare task envs based on toolchains envs
    for taskName, taskParams in viewitems(tasks):

        taskParams['name'] = taskName

        # make variant name for each task: 'buildtype.taskname'
        taskVariant = assist.makeTaskVariantName(buildtype, taskName)
        # store it
        taskParams['$task.variant'] = taskVariant

        # set up env with toolchain for task
        toolchains = toList(taskParams.get('toolchain', []))
        if toolchains:
            baseEnv = toolchainsEnvs.get(toolchains[0], emptyEnv)
            if len(toolchains) > 1:
                # make copy of env to avoid using 'update' on original
                # toolchain env
                baseEnv = assist.copyEnv(baseEnv)
            for toolname in toolchains[1:]:
                baseEnv.update(toolchainsEnvs.get(toolname, emptyEnv))
        else:
            if 'source' in taskParams:
                msg = "No toolchain for task %r found." % taskName
                msg += " Is buildconf correct?"
                conf.fatal(msg)
            else:
                baseEnv = emptyEnv

        # and save selected env (conf.setenv makes the new object that is
        # not desirable here)
        conf.setDirectEnv(taskVariant, baseEnv)

        # Create env for task from root env with cleanup
        taskEnv = conf.makeTaskEnv(taskVariant)

        # conf.setenv with unknown name or non-empty env makes deriving or
        # creates the new object and it is not really needed here
        conf.setDirectEnv(taskVariant, taskEnv)

        # set task env variables
        assist.setTaskEnvVars(conf.env, taskParams)

        # configure all possible task params
        conf.configureTaskParams(bconf, taskParams)

    # run conf checkers
    conf.runConfTests(buildtype, tasks)

    # save envs
    for taskName, taskParams in viewitems(tasks):

        # It's not needed anymore.
        taskParams.pop('conftests', None)

        taskVariant = taskParams['$task.variant']
        conf.setenv(taskVariant)

        # Waf always loads all *_cache.py files in directory 'c4che' during
        # build step. So it loads all stored variants even though they
        # aren't needed. And I decided to save variants in different files and
        # load only needed ones.
        conf.env.store(assist.makeCacheConfFileName(zmcachedir, taskVariant))

        # It's necessary to delete variant from conf.all_envs. Otherwise
        # Waf will store it in 'c4che'
        conf.all_envs.pop(taskVariant, None)

    # Remove unneccesary envs
    for toolchain in toolchainsEnvs:
        conf.all_envs.pop(toolchain, None)

    conf.saveTasksInEnv(bconf)

    # switch current env to the root env
    conf.setenv('')

    conf.addExtraMonitFiles(bconf)

    # gather tasks in subdirs
    subdirs = bconf.subdirs
    if subdirs:
        conf.recurse(subdirs)

def build(bld):
    """
    Implementation for wscript.build
    """

    buildtype = bld.validateVariant()

    bconf = bld.bconfManager.root
    assert id(bconf) == id(bld.getbconf())
    bconfPaths = bconf.confPaths

    isInstall = bld.cmd in ('install', 'uninstall')
    if isInstall:
        assist.applyInstallPaths(bld.env, cli.selected)

    rootEnv = bld.env

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
    tasks = bld.getTasks(buildtype)

    allowedTasks = cli.selected.args.tasks
    if allowedTasks:
        allowedTasks = set(assist.getTaskNamesWithDeps(tasks, allowedTasks))

    for taskName, taskParams in viewitems(tasks):

        if allowedTasks and taskName not in allowedTasks:
            continue

        # set bld.path to startdir of the buildconf from which the current task
        bld.path = bld.getTaskPathNode(taskParams['$startdir'])

        # task env variables are stored in separative env
        # so it's need to switch in
        bld.variant = taskParams.get('$task.variant')

        # load environment for this task
        cacheFile = assist.makeCacheConfFileName(bconfPaths.zmcachedir, bld.variant)
        bld.env = ConfigSet(cacheFile)
        bld.env.parent = rootEnv

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
        dropKeys = KNOWN_TASK_PARAM_NAMES - assist.getUsedWafTaskKeys()
        dropKeys.update([k for k in bldParams if k[0] == '$' ])
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
    Implementation for wscript.distclean
    """

    bconfPaths = ctx.getbconf().confPaths
    assist.distclean(bconfPaths)

def shutdown(_):
    """
    Implementation for wscript.shutdown
    """

    # Do nothing
