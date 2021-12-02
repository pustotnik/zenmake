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
from zm.constants import WAF_CONFIG_LOG, CONFTEST_DIR_PREFIX, CWD
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

_runcmdInfo = {}

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

    # print some info

    if cliArgs.verbose > 1:
        log.info("* ZenMake command line args: %s", " ".join(cli.selected.orig))

    log.info("* Project name: '%s'" % bconf.projectName)
    if bconf.projectVersion:
        log.info("* Project version: %s" % bconf.projectVersion)
    log.info("* Build type: '%s'" % bconf.selectedBuildType)

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

def _getAllowedBuildTaskNames(allTaskNames, allTasks):

    # In some cases like the 'test' command the 'allTaskNames' can contain
    # more items than the 'allTasks'. So we must make actual list names with
    # preserved order.
    allTaskNames = [x for x in allTaskNames if x in allTasks]
    allowedNames = cli.selected.args.tasks
    if not allowedNames:
        return allTaskNames

    _allTaskNames = set(allTaskNames)
    if not set(allowedNames).issubset(_allTaskNames):
        unknownTasks = list(set(allowedNames) - _allTaskNames)
        if len(unknownTasks) == 1:
            msg = "Unknown/disabled task name %r" % unknownTasks[0]
        else:
            msg = "Unknown/disabled task names: %s" % str(unknownTasks)[1:-1]
        raise error.ZenMakeError(msg)

    allowedNames = set(assist.getTaskNamesWithDeps(allTasks, allowedNames))
    # remake as a list from 'allTaskNames' to save order of names
    allowedNames = [x for x in allTaskNames if x in allowedNames]
    return allowedNames

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
    taskNames = _getAllowedBuildTaskNames(bld.zmOrdTaskNames, tasks)

    actualCmdName = cli.selected.name
    if actualCmdName == 'run':
        _runcmdInfo['tasks'] = tasks

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

def run(_):
    """
    Implementation of the 'run' command
    """

    tasks = _runcmdInfo['tasks']

    tname = cli.selected.args.task
    if tname:
        taskParams = tasks.get(tname)
        if taskParams is None:
            # try to find the name in the 'target' param
            for params in tasks.values():
                target = os.path.split(params['target'])[1]
                realTarget = os.path.split(params['$real.target'])[1]
                if tname in (target, realTarget):
                    taskParams = params
                    break

        if taskParams is None:
            msg = "Target '%s' not found" % tname
            raise error.ZenMakeError(msg)
    else:
        # autodetect appropriate task with an executable target
        exeTasks = [ x for x in tasks.values() if x['$tkind'] == 'program']
        if not exeTasks:
            msg = "There are no executable targets to run"
            raise error.ZenMakeError(msg)
        if len(exeTasks) != 1:
            names = [x['name'] for x in exeTasks]
            msg = "There are more than one executable targets to run."
            msg += " You can select one of them: %s" % ", ".join(names)
            raise error.ZenMakeError(msg)

        taskParams = exeTasks[0]

    realTarget = taskParams['$real.target']
    dirpath = os.path.dirname(realTarget)

    relTargetPath = os.path.relpath(realTarget, CWD)
    cmd = '"%s" %s' % (realTarget, ' '.join(cli.selected.notparsed))

    # NOTE: Don't use any arg that can turn on the capture of the output.
    # Otherwise it can produce incorrect order of stdout from a target on Windows.
    kwargs = {
        'cwd' : dirpath,
        'env' : utils.addRTLibPathToOSEnv(dirpath, os.environ.copy()),
        'shell': False,
    }

    log.info("Running '%s' ..." % relTargetPath, extra = { 'c1': log.colors('PINK') } )
    result = utils.runCmd(cmd, **kwargs)
    if result.exitcode != 0:
        log.warn("Program '%s' has finished with exit code %d" \
                            % (relTargetPath, result.exitcode))

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
