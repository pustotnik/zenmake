# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
from copy import deepcopy

from zm.constants import SYSTEM_LIB_PATHS
from zm.pyutils import viewvalues, viewitems, listvalues, maptype
from zm import error, log
from zm.utils import toListSimple, runExternalCmd
from zm.pathutils import PathsParam, getNodesFromPathsDict, pathsDictParamsToList

joinpath   = os.path.join
isabs      = os.path.isabs
pathexists = os.path.exists
normpath   = os.path.normpath
relpath    = os.path.relpath

############# functions to configure dependencies

def _setupDep(bconf, depName, target, taskParams):

    depsConf = bconf.dependencies
    depConf = depsConf.get(depName)
    if depConf is None:
        msg = 'Task %r: dependency %r is unknown.' % \
                (taskParams['name'], depName)
        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    targetConf = depConf.get('targets', {}).get(target)
    if targetConf is None:
        msg = 'Task %r: target %r in dependency %r is not found.' % \
                (taskParams['name'], target, depName)
        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    targetConf['name'] = targetName = targetConf.get('name', target)

    targetType = targetConf['type']
    if targetType == 'shlib':
        libsParamName = 'libs'
        libpathParamName = 'libpath'
    elif targetType == 'stlib':
        libsParamName = 'stlibs'
        libpathParamName = 'stlibpath'
    else:
        return targetConf

    targetPath = targetConf.get('dir', depConf.get('rootdir'))
    if targetPath is not None:
        libpath = taskParams.get(libpathParamName)
        if libpath is None:
            libpath = PathsParam.makeFrom(targetPath, kind = 'paths')
        else:
            libpath.insertFrom(0, targetPath)
        taskParams[libpathParamName] = libpath

    libs = taskParams.get(libsParamName, [])
    libs.append(targetName)
    taskParams[libsParamName] = libs

    monitParamName = 'monit%s' % libsParamName
    taskParams[monitParamName] = taskParams.get(monitParamName, []) + [targetName]

    exportIncludes = depConf.get('export-includes')
    if exportIncludes is not None:
        includes = taskParams.get('includes')
        if includes is None:
            includes = PathsParam.makeFrom(exportIncludes)
        else:
            includes.extendFrom(exportIncludes)
        taskParams['includes'] = includes

    return targetConf

def _calcTargetFileName(targetConf, taskParams):

    pattern = taskParams['$tpatterns'].get(targetConf['type'])
    if pattern is None:
        targetConf['fname'] = targetConf['name']
        return
    filename = pattern % targetConf['name']
    targetConf['fname'] = filename

def _handleTasksWithDeps(bconf):
    """
    Handle tasks with external dependencies.
    Returns dict of found deps with targets.
    """

    deps = set()

    for taskParams in viewvalues(bconf.tasks):

        use = taskParams.get('use')
        if use is None:
            continue

        foundDeps = set()
        for item in use:
            parts = item.split(':')
            if len(parts) == 1:
                continue

            foundDeps.add(item)
            dep, target = parts
            targetConf = _setupDep(bconf, dep, target, taskParams)
            _calcTargetFileName(targetConf, taskParams)
            deps.add(dep)

        # clean up 'use'
        if foundDeps:
            use = [x for x in use if x not in foundDeps]
            if use:
                taskParams['use'] = use
            else:
                taskParams.pop('use', None)

    return list(deps)

def _makeDepTargetsForDb(depParams, rootdir):

    _targets = {}
    targets = depParams.get('targets')
    if targets is None:
        return _targets

    for target in viewvalues(targets):
        params = target.copy()
        if 'dir' in params:
            _dir = params['dir']
            _dir.startdir = rootdir
            params['dir'] = _dir.relpath()
        targetId = repr(sorted(params.items()))
        _targets[targetId] = params

    return _targets

def _setupTriggers(ruleParams):

    ruleName = ruleParams['name']
    triggers = ruleParams['trigger']
    if not triggers:
        if ruleName == 'configure':
            defaultTrigger = { 'no-targets' : True }
        else:
            defaultTrigger = { 'always' : True }

        triggers.update(defaultTrigger)

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

    defaultZmCommands = {
        # rule name -> zm commands
        'configure' : ['configure', 'build'],
        'build'     : ['build'],
    }

    for ruleParams in rules:
        _setupTriggers(ruleParams)

        cmds = ruleParams.pop('zm-commands', None)
        if cmds is None:
            cmds = defaultZmCommands.get(ruleParams['name'], [])
        else:
            cmds = toListSimple(cmds)

        for cmd in cmds:
            producers.setdefault(cmd, [])
            producers[cmd].append(ruleParams)

    # uniqify rules
    for cmdRules in viewvalues(producers):
        seen = {}
        _rules = []
        for ruleParams in cmdRules:
            reprKey = ruleParams.copy()
            reprKey.pop('targets', None)
            reprKey = repr(reprKey)
            seenRule = seen.get(reprKey)
            if seenRule is not None:
                seenTargets = seenRule['targets']
                for target in ruleParams['targets']:
                    if target not in seenTargets:
                        seenTargets.append(target)
            else:
                _rules.append(ruleParams)
                seen[reprKey] = ruleParams

        # replace
        del cmdRules[:]
        cmdRules.extend(sorted(_rules,
                               key = lambda x: _RULE_PRIORITIES[x['name']] ))

    return producers

def configureExternalDeps(bconfManager):
    """
    Configure external dependencies.
    Returns dict with configuration of dependency producers.
    """

    resultRules = []

    rootdir = bconfManager.root.rootdir

    for bconf in bconfManager.configs:
        deps = _handleTasksWithDeps(bconf)
        if not deps:
            continue

        depsConf = bconf.dependencies
        for depName in deps:
            depParams = depsConf[depName]
            depRootDir = depParams.get('rootdir')
            if depRootDir:
                depRootDir.startdir = rootdir

            targets = _makeDepTargetsForDb(depParams, rootdir)
            if not targets:
                log.warn("Dependency %r has not 'targets'" % depName)
                continue

            rules = depParams.get('rules', {})
            for ruleName, ruleParams in viewitems(rules):
                if not isinstance(ruleParams, maptype):
                    ruleParams = { 'cmd' : ruleParams }
                else:
                    # don't change bconf.dependencies
                    ruleParams = deepcopy(ruleParams)

                if not ruleParams.get('cmd'):
                    msg = "Dependency %r: parameter 'cmd' is empty" % depName
                    msg += " for rule %r." % ruleName
                    log.warn(msg)
                    continue

                ruleParams['name'] = ruleName
                ruleParams.setdefault('env', {})
                ruleParams.setdefault('trigger', {})
                ruleParams.setdefault('shell', True)
                ruleParams.setdefault('timeout', None)
                ruleParams.setdefault('zm-commands', None)

                ruleParams.setdefault('cwd', depRootDir)
                cwd = ruleParams['cwd']
                if not cwd:
                    msg = "Dependency %r: parameter 'cwd' is unknown/empty" % depName
                    msg += " for rule %r." % ruleName
                    msg += "\nForgot to set 'rootdir' for the %r ?" % depName
                    raise error.ZenMakeConfError(msg, confpath = bconf.path)

                if cwd != depRootDir:
                    cwd.startdir = rootdir
                ruleParams['cwd'] = cwd.relpath()

                ruleParams['targets'] = targets
                resultRules.append(ruleParams)

    for ruleParams in resultRules:
        ruleParams['targets'] = listvalues(ruleParams['targets'])

    return _dispatchRules(resultRules)

############# functions to use configured dependencies

def _checkTriggerEnv(_, rule):

    envTrigger = rule['trigger'].get('env')
    if not envTrigger:
        return False

    return all(os.environ.get(x) == y for x, y in viewitems(envTrigger))

def _checkTriggerNoTargets(_, rule):

    noTargets = rule['trigger'].get('no-targets')
    if not noTargets:
        return False

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

        pathsDictParamsToList(paths)
        paths = getNodesFromPathsDict(ctx, paths, rootdir, withDirs = True)
        if triggerName == 'paths-exist':
            if paths  and all(x.exists() for x in paths):
                return True
        else:
            if not paths or any(not x.exists() for x in paths):
                return True

    return False

def _checkTriggerFunc(ctx, rule):

    funcAttrs = rule['trigger'].get('func')
    if not funcAttrs:
        return False

    bconfDirPath, funcName = funcAttrs
    bconf = ctx.bconfManager.config(bconfDirPath)
    func = bconf.getattr(funcName)[0]

    kwargs = {
        'zmcmd' : ctx.cmd,
        'targets' : rule['targets'],
    }

    return func(**kwargs)

def _checkTriggers(ctx, rule):

    rootdir = ctx.bconfManager.root.rootdir
    triggers = rule['trigger']

    for target in rule['targets']:
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

    rootbconf = ctx.bconfManager.root
    rootdir = rootbconf.rootdir

    cmd = rule['cmd']
    env = dict(os.environ)
    env.update(rule['env'])
    cwd = joinpath(rootdir, rule['cwd'])

    kwargs = {
        'cwd' : cwd,
        'env' : env,
        'timeout' : rule['timeout'],
        'shell' : rule['shell'],
    }

    ctx.log_command(cmd, kwargs)
    exitcode, stdout, stderr = runExternalCmd(cmd, **kwargs)

    if stdout:
        sys.stdout.write(stdout)
        sys.stdout.flush()
    if stderr:
        sys.stderr.write(stderr)
        sys.stderr.flush()

    if exitcode < 0:
        raise error.ZenMakeProcessFailed(cmd, exitcode)

def produceExternalDeps(ctx):
    """
    Run command for external dependencies
    """

    cmd = ctx.cmd
    cmdConfs = ctx.zmdepconfs.get(cmd)
    if cmdConfs is None:
        return

    printLogo = True
    for rule in cmdConfs:
        doRun = _checkTriggers(ctx, rule)
        if not doRun:
            continue
        if printLogo:
            log.printStep('Running rules for external dependencies')
            printLogo = False
        _runRule(ctx, rule)
