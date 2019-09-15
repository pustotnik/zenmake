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
    'shutdown',
    'APPNAME',
    'VERSION',
]

import os

from waflib.ConfigSet import ConfigSet
from waflib.Build import BuildContext
from zm.pyutils import viewitems
from zm import log, shared, cli, assist
from zm.buildconf.validator import KNOWN_TASK_PARAM_NAMES

# pylint: disable=unused-argument

# these variables are mandatory ('/' are converted automatically)
top = shared.buildConfHandler.confPaths.wscripttop
out = shared.buildConfHandler.confPaths.wscriptout

# mostly for WAF 'dist' command
APPNAME = shared.buildConfHandler.projectName
VERSION = shared.buildConfHandler.projectVersion

def options(opt):
    """
    Implementation for wscript.options
    It's called by Waf as method where cmdline options can be added/removed
    """

    # This method WAF calls before all other methods including 'init'

    # Remove incompatible options
    #opt.parser.remove_option('-o')
    #opt.parser.remove_option('-t')

def init(ctx):
    """
    Implementation for wscript.init
    It's called by Waf before all other commands but after 'options'
    """

    shared.buildConfHandler.handleCmdLineArgs(cli.selected)

    buildtype = shared.buildConfHandler.selectedBuildType

    #pylint: disable=unused-variable,missing-docstring,too-many-ancestors
    from waflib.Build import CleanContext, InstallContext, UninstallContext
    for cls in (BuildContext, CleanContext, InstallContext, UninstallContext):
        class CtxClass(cls):
            pass
    #pylint: enable=unused-variable,missing-docstring,too-many-ancestors

    # set 'variant' for BuildContext and all classes based on BuildContext
    setattr(BuildContext, 'variant', buildtype)

def configure(conf):
    """
    Implementation for wscript.configure
    """

    # See details here: https://gitlab.com/ita1024/waf/issues/1563
    conf.env.NO_LOCK_IN_RUN = True
    conf.env.NO_LOCK_IN_TOP = True

    confHandler = shared.buildConfHandler

    # for assist.runConfTests
    conf.env['PROJECT_NAME'] = confHandler.projectName

    # get root env
    assert conf.variant == ''
    rootEnv = conf.env

    # load all toolchains envs
    toolchainsEnvs = assist.loadToolchains(conf, confHandler, rootEnv)

    zmcachedir = confHandler.confPaths.zmcachedir
    wafcachefile = confHandler.confPaths.wafcachefile
    conf.env.alltasks = assist.loadTasksFromCache(wafcachefile)

    buildtype = confHandler.selectedBuildType
    tasks = confHandler.tasks
    conf.env.alltasks[buildtype] = tasks

    # Prepare task envs based on toolchains envs
    for taskName, taskParams in viewitems(tasks):

        # make variant name for each task: 'buildtype.taskname'
        taskVariant = assist.makeTaskVariantName(buildtype, taskName)
        # store it
        taskParams['$task.variant'] = taskVariant

        # set up env with toolchain for task
        toolchain = taskParams.get('toolchain', None)
        baseEnv = toolchainsEnvs.get(toolchain, rootEnv)

        # and save selected env (conf.setenv makes the new object that is
        # not desirable here)
        assist.setConfDirectEnv(conf, taskVariant, baseEnv)

    # run conf checkers
    assist.runConfTests(conf, buildtype, tasks)

    # Configure tasks
    for taskName, taskParams in viewitems(tasks):

        # It's not needed anymore.
        taskParams.pop('conftests', None)

        taskVariant = taskParams['$task.variant']

        # make deep copy to rid of side effects with different flags
        # in different tasks
        taskEnv = assist.deepcopyEnv(conf.all_envs.pop(taskVariant))

        # conf.setenv with unknown name or non-empty env makes deriving or
        # creates the new object and it is not really needed here
        assist.setConfDirectEnv(conf, taskVariant, taskEnv)

        # set variables
        assist.setTaskEnvVars(conf.env, taskParams)

        # configure all possible task params
        assist.configureTaskParams(conf, confHandler, taskName, taskParams)

        # Waf always loads all *_cache.py files in directory 'c4che' during
        # build step. So it loads all stored variants even though they
        # aren't needed. And I decided to save variants in different files and
        # load only needed ones.
        conf.env.store(assist.makeCacheConfFileName(zmcachedir, taskVariant))

        # It's necessary to delete variant from conf.all_envs otherwise
        # waf will store it in 'c4che'
        conf.all_envs.pop(taskVariant, None)

    # reset current env
    conf.setenv('')

    # Remove unneccesary envs
    for toolchain in toolchainsEnvs:
        conf.all_envs.pop(toolchain, None)

    assist.dumpZenMakeCommonFile(confHandler.confPaths)

def validateVariant(ctx):
    """ Check current variant and return it """

    if ctx.variant is None:
        ctx.fatal('No variant!')

    buildtype = ctx.variant
    if buildtype not in ctx.env.alltasks:
        if ctx.cmd == 'clean':
            log.info("Buildtype '%s' not found. Nothing to clean" % buildtype)
            return None
        ctx.fatal("Buildtype '%s' not found! Was step 'configure' missed?"
                  % buildtype)
    return buildtype

def build(bld):
    """
    Implementation for wscript.build
    """

    buildtype = validateVariant(bld)
    if not buildtype:
        return
    bconfPaths = shared.buildConfHandler.confPaths

    # Some comments just to remember some details.
    # - ctx.path represents the path to the wscript file being executed
    # - ctx.root is the root of the file system or the folder containing
    #   the drive letters (win32 systems)

    # Path must be relative
    srcDir = os.path.relpath(bconfPaths.srcroot, bconfPaths.wscriptdir)
    # Since ant_glob can traverse both source and build folders, it is a best
    # practice to call this method only from the most specific build node.
    srcDirNode = bld.path.find_dir(srcDir)

    tasks = bld.env.alltasks[buildtype]
    allowedTasks = cli.selected.args.tasks

    for taskName, taskParams in viewitems(tasks):

        if allowedTasks and taskName not in allowedTasks:
            continue

        # task env variables are stored in separative env
        # so it's need to switch in
        bld.variant = taskParams.get('$task.variant')

        # load environment for this task
        cacheFile = assist.makeCacheConfFileName(bconfPaths.zmcachedir, bld.variant)
        bld.all_envs[bld.variant] = ConfigSet(cacheFile)

        if 'source' in taskParams:
            taskParams['source'] = assist.handleTaskSourceParam(taskParams, srcDirNode)

        bldParams = taskParams.copy()
        # Remove params that can conflict with waf in theory
        dropKeys = (set(KNOWN_TASK_PARAM_NAMES) - assist.getUsedWafTaskKeys())
        dropKeys.update([k for k in bldParams if k[0] == '$' ])
        for k in dropKeys:
            bldParams.pop(k, None)

        #special param
        bldParams['zm-task-params'] = taskParams

        # create build task generator
        bld(**bldParams)

    # It's neccesary to revert to origin variant otherwise WAF won't find
    # correct path at the end of the building step.
    bld.variant = buildtype

def shutdown(ctx):
    """
    Implementation for wscript.shutdown
    """

    # Do nothing at this moment
