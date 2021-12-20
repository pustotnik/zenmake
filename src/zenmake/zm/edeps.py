# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import shutil
from copy import deepcopy
from collections import defaultdict

from zm.constants import DEPNAME_DELIMITER, SYSTEM_LIB_PATHS, PYTHON_EXE, PLATFORM
from zm.pyutils import maptype, stringtype
from zm import error, log, db, cli, utils
from zm.pathutils import PathsParam, getNodesFromPathsConf
from zm.buildconf import loader as buildconfLoader
from zm.buildconf.validator import Validator
from zm.buildconf.processing import Config as BuildConfig
from zm.waf import assist

joinpath    = os.path.join
isabs       = os.path.isabs
pathexists  = os.path.exists
pathlexists = os.path.lexists
normpath    = os.path.normpath
relpath     = os.path.relpath
findConfFile = buildconfLoader.findConfFile
hashRtObj = utils.hashOrdObj

symlink = getattr(os, "symlink", None)
symlink = None if not callable(symlink) else symlink

ZM_RUN = '%s %s' % (PYTHON_EXE, sys.argv[0])

_local = {}

######################################################################
############# PREPARE CONFIGURATION OF EXTERNAL DEPENDENCIES

def _handleTasksWithDeps(bconf, allTasks):
    """
    Handle tasks with external dependencies.
    Returns names of found deps.
    """

    depNames = set()
    depsConf = bconf.edeps

    for taskParams in bconf.tasks.values():

        use = taskParams.get('use')
        if use is None:
            continue

        foundItems = []
        for item in use:
            if item.find(DEPNAME_DELIMITER) >= 0:
                foundItems.append(item)
                continue

            depTaskParams = allTasks.get(item)
            if depTaskParams:
                depTaskParams['$parent'] = taskParams['name']

        if not foundItems:
            continue

        taskDeps = defaultdict(list)

        foundItems = utils.uniqueListWithOrder(foundItems)
        for item in foundItems:
            depName, useName = item.split(DEPNAME_DELIMITER)

            if depName not in depsConf:
                msg = 'Task %r: dependency %r is unknown.' % \
                        (taskParams['name'], depName)
                raise error.ZenMakeConfError(msg, confpath = bconf.path)

            if not useName:
                continue

            taskDeps[depName].append(useName)
            depNames.add(depName)

        taskParams['$external-deps'] = dict(taskDeps)

        # clean up 'use'
        use = [x for x in use if x not in foundItems]
        if use:
            taskParams['use'] = use
        else:
            taskParams.pop('use', None)

    return list(depNames)

_DEFAULT_TRIGGERS = defaultdict(
    lambda: { 'always' : False }, # default for any rule
    configure = { 'always' : True },
    build = { 'no-targets' : True },
)

def _setupTriggers(ruleParams):

    ruleName = ruleParams['name']
    triggers = ruleParams['trigger']
    if not triggers:
        triggers.update(_DEFAULT_TRIGGERS[ruleName])

_RULE_PRIORITIES = {
    'clean' : 1,
    'configure' : 2,
    'build' : 3,
    'test' : 4,
    'install' : 5,
    'uninstall' : 6,
}

def _dispatchRules(rules):

    producers = {}

    for ruleParams in rules:
        _setupTriggers(ruleParams)

        cmds = ruleParams.pop('zm-commands', None)
        if cmds is None:
            # by default rule is called in zm command with the same name
            cmds = [ruleParams['name']]
        else:
            cmds = utils.toListSimple(cmds)

        for cmd in cmds:
            cmdRules = producers.setdefault(cmd, [])
            cmdRules.append(ruleParams)

    # uniqify rules
    for cmdRules in producers.values():
        seen = {}
        _rules = []
        for ruleParams in cmdRules:
            reprKey = ruleParams.copy()
            reprKey.pop('$from-deps', None)
            reprKey = hashRtObj(reprKey)
            seenRule = seen.get(reprKey)
            if seenRule is not None:
                seenDeps = seenRule['$from-deps']
                seenDepsIds = { hashRtObj(x) for x in seenDeps }
                for dep in ruleParams['$from-deps']:
                    if hashRtObj(dep) not in seenDepsIds:
                        seenDeps.append(dep)
            else:
                _rules.append(ruleParams)
                seen[reprKey] = ruleParams

        # replace
        del cmdRules[:]
        cmdRules.extend(sorted(_rules,
                               key = lambda x: _RULE_PRIORITIES[x['name']] ))

    return producers

def _detectZenMakeProjectRules(depConf, buildtype):

    depRootDir = depConf['rootdir']
    projectRoot = depRootDir.abspath()
    bconfFilePath = findConfFile(projectRoot)
    if bconfFilePath is None:
        # it is not zenmake project
        return

    depConf['$dep-type'] = 'zenmake'
    buildtype = depConf.get('buildtypes-map', {}).get(buildtype, buildtype)

    depBuildConf = buildconfLoader.load(projectRoot, bconfFilePath)
    Validator(depBuildConf).run(checksOnly = True)
    # This call can be optimized because it needs only confPaths here
    # but it doesn't seem that it makes noticeable performance regression
    depBConfPaths = BuildConfig(depBuildConf).confPaths

    depConf['$zmcachedir'] = depBConfPaths.zmcachedir

    if 'rules' in depConf:
        # do nothing if custom rules exist
        return

    cmdArgs = '--buildtype %s' % buildtype

    def needToConfigure(**kwargs):
        # pylint: disable = unused-argument
        zmMetaConf = assist.loadZenMakeMetaFile(depBConfPaths.zmmetafile)
        if not zmMetaConf:
            return True

        depRootDir = depBConfPaths.rootdir
        depZmCacheDir = depBConfPaths.zmcachedir

        # It will be no problem with empty cliargs if you don't use
        # monitored cli args in cmdArgs
        assert not any(x in cmdArgs for x in assist.getMonitoredCliArgNames())
        cliargs = {}

        return assist.needToConfigure(zmMetaConf, depRootDir,
                                      depZmCacheDir, buildtype, cliargs)

    baseRule = {
        'cwd' : depRootDir,
        'shell' : False,
        '$dep-type' : 'zenmake',
    }

    rules = {
        'configure': dict(baseRule, **{
            'cmd' : '%s %s %s' % (ZM_RUN, 'configure', cmdArgs),
            'trigger' : { 'func' : utils.BuildConfFunc(needToConfigure) },
            'zm-commands' : ['configure'],
        }),
        'build' : dict(baseRule, **{
            'cmd' : '%s %s %s' % (ZM_RUN, 'build', cmdArgs),
            'trigger' : { 'always' : True },
            'zm-commands' : ['build'],
        }),
        'test' : dict(baseRule, **{
            'cmd' : '%s %s %s' % (ZM_RUN, 'test', cmdArgs),
            'trigger' : { 'always' : False },
            'zm-commands' : ['test'],
        }),
        'clean' : dict(baseRule, **{
            'cmd' : '%s %s %s' % (ZM_RUN, 'clean', cmdArgs),
            'trigger' : { 'always' : False },
            'zm-commands' : ['clean'],
        }),
        'install' : dict(baseRule, **{
            'cmd' : '%s %s %s' % (ZM_RUN, 'install', cmdArgs),
            'trigger' : { 'always' : False },
            'zm-commands' : ['install'],
        }),
        'uninstall' : dict(baseRule, **{
            'cmd' : '%s %s %s' % (ZM_RUN, 'uninstall', cmdArgs),
            'trigger' : { 'always' : False },
            'zm-commands' : ['uninstall'],
        }),
    }

    depConf['rules'] = rules

def _initRule(ruleName, ruleParams, rootdir, depRootDir):

    if not isinstance(ruleParams, maptype):
        ruleParams = { 'cmd' : ruleParams }
    else:
        # don't change bconf.edeps
        ruleParams = deepcopy(ruleParams)

    ruleParams['name'] = ruleName
    ruleParams.setdefault('env', {})
    ruleParams.setdefault('trigger', {})
    ruleParams.setdefault('shell', False)
    ruleParams.setdefault('timeout', None)
    ruleParams.setdefault('zm-commands', None)

    ruleParams.setdefault('cwd', depRootDir)
    cwd = ruleParams['cwd']
    ruleParams['cwd'] = cwd.relpath(rootdir)

    return ruleParams

def preconfigureExternalDeps(cfgCtx):
    """
    Configure external dependencies.
    Returns dict with configuration of dependency producers ready to use
    in ZenMake command 'configure' but not in others.
    """

    resultRules = []

    bconfManager = cfgCtx.bconfManager
    allTasks = cfgCtx.allTasks
    rootdir = bconfManager.root.rootdir
    buildtype = bconfManager.root.selectedBuildType

    for bconf in bconfManager.configs:
        deps = _handleTasksWithDeps(bconf, allTasks)
        if not deps:
            continue

        depConfs = bconf.edeps
        for depName in deps:
            depConf = depConfs[depName]
            depConf['name'] = depName
            depRootDir = depConf.get('rootdir')
            if depRootDir is None:
                msg = "Dependency %r has no 'rootdir'." % depName
                raise error.ZenMakeConfError(msg, confpath = bconf.path)

            _detectZenMakeProjectRules(depConf, buildtype)

            rules = depConf.get('rules', {})
            for ruleName, ruleParams in rules.items():

                ruleParams = _initRule(ruleName, ruleParams, rootdir, depRootDir)

                if not ruleParams.get('cmd'):
                    msg = "Dependency %r: parameter 'cmd' is empty" % depName
                    msg += " for rule %r." % ruleName
                    log.warn(msg)
                    continue

                ruleParams['$from-deps'] = [depConf]
                resultRules.append(ruleParams)

    cfgCtx.zmdepconfs = _dispatchRules(resultRules)

######################################################################
############# FINISH CONFIGURATION OF EXTERNAL DEPENDENCIES

def _setupTargetFileName(ctx, targetConf, taskParams):

    if targetConf.get('fname'):
        return

    env = ctx.all_envs[taskParams['$task.variant']]
    baseName = targetConf['name']
    targetKind = targetConf['type']
    pattern = taskParams['$tpatterns'].get(targetKind)
    verNum = targetConf.get('ver-num')
    realTarget = assist.makeTargetRealName(baseName, targetKind, pattern,
                                           env, verNum)
    targetConf['fname'] = realTarget

def _addLibPathToTask(taskParams, paramName, newPath):
    libpath = taskParams.get(paramName)
    if libpath is None:
        libpath = PathsParam.makeFrom(newPath, kind = 'paths')
    else:
        libpath.insertFrom(0, newPath)
    taskParams[paramName] = libpath

def _updateTaskLibs(ctx, taskParams, libAttr, libPathAttr):

    libsParamName, libName = libAttr
    libPathParamName, libPath = libPathAttr
    depLibsParamName = '$external-deps-%s' % libsParamName

    allTasks = ctx.allTasks
    while True:
        deplibs = taskParams.setdefault(depLibsParamName, [])
        deplibs.append(libName)

        if libPath:
            _addLibPathToTask(taskParams, libPathParamName, libPath)

        parent = taskParams.get('$parent')
        if not parent:
            break
        taskParams = allTasks[parent]

def _setupTaskDepTarget(ctx, depConf, targetConf, taskParams):

    _setupTargetFileName(ctx, targetConf, taskParams)

    targetType = targetConf['type']
    if targetType == 'shlib':
        libsParamName = 'libs'
        libpathParamName = 'libpath'
    elif targetType == 'stlib':
        libsParamName = 'stlibs'
        libpathParamName = 'stlibpath'
    else:
        return

    libName = targetConf['name']
    depRootDir = depConf['rootdir']
    targetPath = targetConf.get('dir', depRootDir)

    lib = (libsParamName, libName)
    libPath = (libpathParamName, targetPath)
    _updateTaskLibs(ctx, taskParams, lib, libPath)

    monitParamName = 'monit%s' % libsParamName
    taskParams[monitParamName] = taskParams.get(monitParamName, []) + [libName]

def _prepareZenMakeProjectDep(depConf, buildtype, rootdir):

    if depConf.get('$zm-targets-ready', False):
        return []

    buildtype = depConf.get('buildtypes-map', {}).get(buildtype, buildtype)
    cachedir = depConf['$zmcachedir']
    dbTargetsPath = assist.makeTargetsCachePath(cachedir, buildtype)
    dbfile = db.PyDBFile(dbTargetsPath)
    targetsData = dbfile.load()

    targetsRootDir = targetsData['rootdir']

    # == gather targets of sub deps and adjust dir paths
    subDepTargets = targetsData['deptargets']
    for subtarget in subDepTargets:
        absDirPath = normpath(joinpath(targetsRootDir, subtarget['dir']))
        subtarget['dir'] = relpath(absDirPath, rootdir)

    # == handle current targets

    # set all existing targets if no custom targets
    targetConfs = depConf.setdefault('targets', targetsData['targets'])

    targetsBTypeDir = normpath(joinpath(targetsRootDir, targetsData['btypedir']))
    for target in targetConfs.values():
        # zenmake db doesn't have field 'dir' in target confs
        target['dir'] = PathsParam(targetsBTypeDir, rootdir, kind = 'path')

    depConf['$zm-targets-ready'] = True
    return subDepTargets

def _setupTaskDeps(ctx, bconf, taskParams):

    depsConf = bconf.edeps
    taskDeps = taskParams.get('$external-deps', {})
    buildtype = bconf.selectedBuildType
    rootdir = bconf.rootdir
    depTargets = []

    for depName, useNames in taskDeps.items():
        depConf = depsConf[depName]

        exportIncludes = depConf.get('export-includes')
        if exportIncludes is not None:
            includes = taskParams.get('includes')
            if includes is None:
                includes = PathsParam.makeFrom(exportIncludes)
            else:
                includes.extendFrom(exportIncludes)
            taskParams['includes'] = includes

        depType = depConf.get('$dep-type')
        if depType == 'zenmake':
            depTargets.extend(
                _prepareZenMakeProjectDep(depConf, buildtype, rootdir))

        targetConfs = depConf.get('targets', {})

        for targetRefName in useNames:
            targetConf = targetConfs.get(targetRefName)
            if targetConf is None:
                msg = 'Task %r: target %r in dependency %r was not found.' % \
                        (taskParams['name'], targetRefName, depName)
                raise error.ZenMakeConfError(msg, confpath = bconf.path)

            if 'type' not in targetConf:
                msg = "Task %r: target %r in dependency %r has no 'type'." % \
                        (taskParams['name'], targetRefName, depName)
                raise error.ZenMakeConfError(msg, confpath = bconf.path)

            targetConf['name'] = targetConf.get('name', targetRefName)
            _setupTaskDepTarget(ctx, depConf, targetConf, taskParams)

            # add target to list of all dep targets
            depTarget = targetConf.copy()
            depTarget['dir'] = depTarget['dir'].relpath(rootdir)
            depTargets.append(depTarget)

    taskEnv = ctx.all_envs[taskParams['$task.variant']]
    for depTarget in depTargets:
        # We suggest that dep target has the same destinations OS and bin format
        # as the task
        if 'dest-os' not in depTarget:
            depTarget['dest-os'] = taskEnv.DEST_OS
        if 'dest-binfmt' not in depTarget:
            depTarget['dest-binfmt'] = taskEnv.DEST_BINFMT

    return depTargets

def _makeDepTargetsForDb(depConf, rootdir):

    _targets = []
    for target in depConf.get('targets', {}).values():
        _dir = target.get('dir')
        if _dir:
            target['dir'] = _dir.relpath(rootdir)
        _targets.append(target)

    return _targets

def finishExternalDepsConfig(cfgCtx):
    """
    Finish configuring of external dependencies.
    """

    zmdepconfs = cfgCtx.zmdepconfs
    if not zmdepconfs:
        return

    bconfManager = cfgCtx.bconfManager
    rootdir = bconfManager.root.rootdir

    ### set up tasks

    depTargets = []
    for bconf in bconfManager.configs:
        for taskParams in bconf.tasks.values():
            depTargets.extend(_setupTaskDeps(cfgCtx, bconf, taskParams))

    ### set up rule targets

    depConfToRules = {}
    seenRules = set()
    for rules in zmdepconfs.values():
        for rule in rules:
            if hashRtObj(rule) in seenRules:
                continue
            rule['targets'] = []
            fromDeps = rule.pop('$from-deps')
            for depConf in fromDeps:
                _depRules = depConfToRules.setdefault(hashRtObj(depConf), [depConf, []])
                _depRules[1].append(rule)
            seenRules.add(hashRtObj(rule))

    for depConf, rules in depConfToRules.values():
        targets = _makeDepTargetsForDb(depConf, rootdir)
        if not targets:
            log.warn("Dependency %r has no field 'targets'" % depConf['name'])
            continue
        for rule in rules:
            rule['targets'].extend(targets)

    ### make list of all dep targets

    # uniqify all dep targets
    depTargets = utils.uniqueDictListWithOrder(depTargets)

    zmdepconfs['$all-dep-targets'] = depTargets

def applyExternalDepLibsToTasks(tasks):
    """
    Insert libs/stlibs into params 'libs'/'stlibs' in build tasks
    """

    for taskParams in tasks:
        for param in ('libs', 'stlibs'):
            depLibs = taskParams.pop('$external-deps-%s' % param, None)
            if not depLibs:
                continue
            libs = taskParams.setdefault(param, [])
            # A library which calls an external function defined in another library
            # should appear before the library containing the function.
            libs[0:0] = depLibs

######################################################################
############# PRODUCE EXTERNAL DEPENDENCIES

def _checkTriggerEnv(_, rule):

    envTrigger = rule['trigger'].get('env')
    if not envTrigger:
        return False

    return all(os.environ.get(x) == y for x, y in envTrigger.items())

def _checkTriggerNoTargets(ctx, rule):

    noTargets = rule['trigger'].get('no-targets')
    if noTargets is None:
        return False

    if ctx.cmd == 'configure':
        msg = "Trigger 'no-targets' cannot be used in command 'configure'"
        raise error.ZenMakeConfError(msg)

    result = False
    for target in rule['targets']:
        dirpath = target.get('dir')
        dirpaths = [dirpath] if dirpath else []
        dirpaths += SYSTEM_LIB_PATHS

        targetExists = False
        for path in dirpaths:
            if pathexists(joinpath(path, target['fname'])):
                targetExists = True
                break

        if not targetExists:
            if noTargets:
                return True
            break
    else:
        result = not noTargets

    return result

def _checkTriggerPathsExist(ctx, rule):

    rootdir = ctx.bconfManager.root.rootdir

    for triggerName in ('paths-dont-exist', 'paths-exist'):

        paths = rule['trigger'].get(triggerName)
        if not paths:
            continue

        try:
            paths = getNodesFromPathsConf(ctx, paths, rootdir, withDirs = True)
            paths = list(paths)
            pathsExist = True
        except error.ZenMakePathNotFoundError:
            pathsExist = False
            paths = None

        if triggerName == 'paths-exist':
            if paths and pathsExist:
                return True
        else:
            if not paths or not pathsExist:
                return True

    return False

def _checkTriggerFunc(ctx, rule):

    func = rule['trigger'].get('func')
    if not func:
        return False

    if isinstance(func, stringtype):
        bconfFilePath, funcName, _ = func.split(':')
        bconfDirPath = os.path.split(bconfFilePath)[0]
        bconf = ctx.bconfManager.config(bconfDirPath)
        func = bconf.getattr(funcName)[0]
    else:
        # must be utils.BuildConfFunc
        func = func.func

    kwargs = {
        'zmcmd' : ctx.cmd,
        'targets' : rule.get('targets'),
    }

    return func(**kwargs)

def _checkTriggers(ctx, rule):

    rootdir = ctx.bconfManager.root.rootdir
    triggers = rule['trigger']

    for target in rule.get('targets', []):
        dirpath = target.get('dir')
        if dirpath:
            target['dir'] = normpath(joinpath(rootdir, dirpath))

    if triggers.get('always', False):
        return True

    if _checkTriggerEnv(ctx, rule):
        return True

    if _checkTriggerNoTargets(ctx, rule):
        return True

    if _checkTriggerPathsExist(ctx, rule):
        return True

    if _checkTriggerFunc(ctx, rule):
        return True

    return False

def _runRule(ctx, rule):

    depType = rule.get('$dep-type')

    rootbconf = ctx.bconfManager.root
    rootdir = rootbconf.rootdir

    cmd = rule['cmd']
    env = dict(os.environ)
    if depType == 'zenmake':
        cmd += ' --color %s' % ('yes' if log.colorsEnabled() else 'no')
        if _local.get('configure-cmd-was-called', False):
            # optimization: avoid needless work to autodetect running of 'configure'
            env['ZENMAKE_AUTOCONFIG'] = 'false'
        forceRules = cli.selected.args.get('forceExternalDeps')
        if forceRules:
            cmd += ' --force-edeps'

    env.update(rule['env'])
    cwd = joinpath(rootdir, rule['cwd'])

    kwargs = {
        'cwd' : cwd,
        'env' : env,
        'timeout' : rule['timeout'],
        'shell' : rule['shell'],
    }

    ctx.log_command(cmd, kwargs)

    def printLine(line, err):
        line = '  %s' % line
        stream = sys.stderr if err else sys.stdout
        stream.write(line)
        stream.flush()

    kwargs['outCallback'] = printLine
    result = utils.runCmd(cmd, **kwargs)
    if result.exitcode != 0:
        raise error.ZenMakeProcessFailed(cmd, result.exitcode)

def _getAllTargetFiles(target):

    targetType = target['type']
    targetOS = target['dest-os']
    targetBinFmt = target['dest-binfmt']

    names = [target['fname']]

    verNum = target.get('ver-num')
    if not verNum or targetType != 'shlib' or \
        targetBinFmt not in ('elf', 'mac-o') or targetOS == 'openbsd':
        return names

    # number of soname/compatibility_version
    cnumber = verNum.split('.')[0]
    libName = names[0]

    if libName.endswith('.dylib'):
        baseName = libName[:len(libName)-6]
        template = '%s.%s.dylib'
    else:
        baseName = libName
        template = '%s.%s'

    names.append(template % (baseName, verNum))
    if cnumber != verNum:
        names.append(template % (baseName, cnumber))

    return names

def _syncTargetFile(src, dst, makesymlink):

    if not pathexists(src):
        return

    if pathlexists(dst):
        # remove
        os.unlink(dst)

    if makesymlink:
        if symlink is None:
            shutil.copy2(src, dst)
        else:
            symlink(src, dst)
    else:
        shutil.copy2(src, dst)

def _provideDepTargetFiles(ctx):

    rootbconf = ctx.bconfManager.root
    rootdir = rootbconf.rootdir
    btypeDir = rootbconf.selectedBuildTypeDir

    allDepTargets = ctx.zmdepconfs['$all-dep-targets']

    paths = []
    for target in allDepTargets:
        targetType = target['type']
        if targetType == 'stlib':
            # don't copy/symlink static libs
            continue
        fnames = _getAllTargetFiles(target)
        dirpath = normpath(joinpath(rootdir, target['dir']))
        paths.extend('%s%s%s' % (dirpath, os.sep, x) for x in fnames)

    makesymlink = PLATFORM != 'windows'
    for path in paths:
        resultPath = joinpath(btypeDir, os.path.basename(path))
        _syncTargetFile(path, resultPath, makesymlink)

def produceExternalDeps(ctx):
    """
    Run commands for external dependencies
    """

    cmd = ctx.cmd
    rules = ctx.zmdepconfs.get(cmd)
    if rules is None:
        return

    forceRules = cli.selected.args.get('forceExternalDeps')

    printLogo = True
    for rule in rules:
        doRun = True if forceRules else _checkTriggers(ctx, rule)
        if not doRun:
            continue
        if printLogo:
            log.printStep('Running rules for external dependencies')
            printLogo = False
        _runRule(ctx, rule)

    bconfFeatures = ctx.bconfManager.root.general
    if cmd == 'build' and bconfFeatures.get('provide-edep-targets', False):
        _provideDepTargetFiles(ctx)

    if cmd == 'configure':
        _local['configure-cmd-was-called'] = True
        # it's not needed anymore
        ctx.zmdepconfs.pop(cmd, None)
