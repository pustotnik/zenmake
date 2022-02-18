# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module adds Waf feature 'runcmd' in tasks
"""

import os
import re
import shlex

from waflib.TaskGen import feature, after
from waflib import Task
from zm.constants import EXE_FILE_EXTS, PYTHON_EXE
from zm.pyutils import maptype, stringtype
from zm import log, error
from zm.utils import cmdHasShellSymbols, substVars, substBuiltInVars, addRTLibPathsToOSEnv
from zm.pathutils import PathsParam
from zm.features import postcmd
from zm.waf.assist import gatherRtLibPaths

_normpath = os.path.normpath
_relpath = os.path.relpath

_RE_STARTS_WITH_SUBST = re.compile(r'\s*\$[\{\(]', re.ASCII)

RUNBY_FILE_EXT = {
    '.py'  : ['python3', 'python'],
    '.pl'  : ['perl'],
    '.lua' : ['lua'],
    '.rb'  : ['ruby'],
}

def _splitCmdLine(cmdline, taskName, bconfPath):

    posixMode = os.name == 'posix'
    try:
        cmdSplitted = shlex.split(cmdline, posix = posixMode)
    except ValueError as ex:
        # "No closing quotation" or "No escaped character"
        msg = "Task %r: command line %r is invalid (%s)" % (taskName, cmdline, ex)
        raise error.ZenMakeConfError(msg, confpath = bconfPath)

    return cmdSplitted

def _makeCmdForScript(cmdline, cmdExt, findfunc):

    cmdExt = cmdExt.strip("'").strip('"')
    # try to detect interpreter for some cases
    launchers = RUNBY_FILE_EXT.get(cmdExt)
    if not launchers:
        return None

    launcherPath = None
    for launcher in launchers:
        result = findfunc(launcher)
        if result:
            launcherPath = result[0]
            break

    if not launcherPath and cmdExt == '.py':
        launcherPath = PYTHON_EXE
    if launcherPath:
        return '%s %s' % (launcherPath, cmdline)

    return None

def _processCmdLine(ctx, taskParams):
    """ Get and process 'cmd' """

    startNode = ctx.getStartDirNode(taskParams['$startdir'])

    bconf      = ctx.getbconf(startNode)
    btypeDir   = bconf.selectedBuildTypeDir
    startdir   = bconf.startdir
    cmdArgs    = taskParams['run']

    # By default 'shell' is True to get rid of some problems with Waf and Windows
    shell = cmdArgs.get('shell', True)

    cmdline = cmdArgs.get('cmd', '').strip()
    if not cmdline and taskParams['$runnable']:
        cmdline = taskParams['$real.target']

    if not cmdline:
        return cmdline, shell

    extraArgs = cmdArgs.get('extra-args')
    if extraArgs:
        cmdline = '%s %s' % (cmdline, ' '.join(extraArgs))

    shell = cmdHasShellSymbols(cmdline) if not shell else shell
    cmdSplitted = _splitCmdLine(cmdline, taskParams['name'], bconf.path)
    if not shell:
        # Waf cannot work correctly with paths with whitespaces when
        # 'shell' is False.
        # TODO: try to make solution for 'shell' == False
        if any(' ' in s for s in cmdSplitted):
            shell = True

    paths = [cmdArgs['cwd'], startdir, btypeDir]
    paths.extend(os.environ.get('PATH', '').split(os.pathsep))
    fkw = {
        'path_list' : paths, 'quiet' : True,
        'exts' : EXE_FILE_EXTS, 'mandatory' : False
    }

    partsCount = len(cmdSplitted)
    launcher = cmdSplitted[0]
    cmdExt = os.path.splitext(launcher)[1]
    if partsCount == 1 and cmdExt:
        find = lambda x: ctx.find_program(x, **fkw)
        result = _makeCmdForScript(cmdline, cmdExt, find)
        if result:
            cmdline = result

    elif partsCount > 1 and not shell and not _RE_STARTS_WITH_SUBST.match(launcher):
        # Waf raises exception in verbose mode with 'shell' == False if it
        # cannot find full path to executable and on windows cmdline
        # like 'python file.py' doesn't work.
        # So here is the attempt to find full path for such a case.
        result = ctx.find_program(launcher, **fkw)
        if result:
            launcher = result[0]
            cmdSplitted[0] = launcher
            cmdSplitted = [ x.replace(r'"', r'\"') for x in cmdSplitted]
            cmdline = ' '.join('"%s"' % s if ' ' in s else s for s in cmdSplitted)

    return cmdline, shell

@postcmd('configure')
def postConf(conf):
    """ Prepare task params after wscript.configure """

    rootbconf = conf.bconfManager.root
    btypeDir  = rootbconf.selectedBuildTypeDir
    rootdir   = rootbconf.rootdir

    for taskParams in conf.allOrderedTasks:

        features = taskParams['features']
        cmdArgs = taskParams.get('run', None)

        if 'runcmd' not in features:
            if cmdArgs is not None:
                features.append('runcmd')
            else:
                continue

        if cmdArgs is None:
            cmdArgs = {}
        elif not isinstance(cmdArgs, maptype):
            cmdArgs = { 'cmd' : cmdArgs }

        cmdArgs.update({
            'name'   : taskParams['name'],
            'timeout': cmdArgs.get('timeout', None),
            'env'    : cmdArgs.get('env', {}),
            'repeat' : cmdArgs.get('repeat', 1),
        })

        taskParams['run'] = cmdArgs

        cwd = cmdArgs.get('cwd', None)
        if cwd:
            try:
                cwd = cwd.abspath()
            except AttributeError:
                startdir = cmdArgs.get('startdir', taskParams['$bconf'].startdir)
                cwd = PathsParam(cwd, startdir, rootdir).abspath()
        else:
            cwd = btypeDir
        cmdArgs['cwd'] = cwd

        cmdArgs['$type'] = ''
        cmd = cmdArgs.get('cmd', None)
        if cmd and callable(cmd):
            # it's needed because a function cannot be saved in a file as is
            cmdArgs['cmd'] = cmd.__name__
            cmdArgs['shell'] = False
            cmdArgs['$type'] = 'func'

def _fixRunCmdDepsOrder(tgen):
    """ Fix order of running """

    ctx = tgen.bld
    runcmdTask = tgen.runcmdTask
    standalone = True

    linkTask = getattr(tgen, 'link_task', None)
    if linkTask:
        runcmdTask.set_run_after(linkTask)
        standalone = False

    zmTaskParams = getattr(tgen, 'zm-task-params', {})

    if standalone:
        runBefore = zmTaskParams['$run-task-before-tgen'] = []
        for rdepName in zmTaskParams.get('$ruse', []):
            runBefore.append((runcmdTask, rdepName))

    for dep in zmTaskParams.get('use', []):
        try:
            other = ctx.get_tgen_by_name(dep)
        except error.WafError:
            continue

        # Ensure that the other task generator has created its tasks
        other.post()

        depTask = getattr(other, 'runcmdTask', None)
        if not depTask:
            depTask = getattr(other, 'link_task', None)
        if not depTask:
            # better than nothing
            depTask = other.tasks[0]

        runcmdTask.set_run_after(depTask)

def _isCmdStandalone(tgen):
    """ Detect if current runcmd is standalone """
    features = getattr(tgen, 'features', [])
    otherFeatures = set(features) - set(('runcmd', ))
    return not otherFeatures and getattr(tgen, 'rule', None) is None

def _createRunCmdTask(tgen, ruleArgs):
    """ Create new rule task for runcmd """

    classParams = {
        'shell' : ruleArgs['shell'],
        'func'  : ruleArgs['rule'],
        'color' : ruleArgs['color'],
    }

    name = '%s[runcmd]' % tgen.name
    cls = Task.task_factory(name, **classParams)

    setattr(cls, '__str__', lambda _: 'command for task %r' % tgen.name)
    setattr(cls, 'keyword', ruleArgs['cls_keyword'])
    if ruleArgs.get('deep_inputs', False):
        Task.deep_inputs(cls)

    task = tgen.create_task(name)
    for k in ('after', 'before', 'ext_in', 'ext_out'):
        setattr(task, k, ruleArgs.get(k, []))
    for k in ('timeout', 'cwd', 'env'):
        setattr(task, k, ruleArgs[k])

    return task

def _createRuleWithFunc(bconf, funcName):

    bconfPaths  = bconf.confPaths
    func = bconf.getattr(funcName)[0]

    def runFunc(task):
        tgen = task.generator
        zmTaskParams = getattr(tgen, 'zm-task-params', {})
        args = {
            'taskname'  : tgen.name,
            'startdir'  : bconfPaths.startdir,
            'buildroot' : bconfPaths.buildroot,
            'buildtype' : bconf.selectedBuildType,
            'waftask'   : task,
        }
        target = zmTaskParams.get('$real.target', '')
        if target:
            args['target'] = target
        func(args)

    return runFunc

def _makeCmdRuleArgs(tgen):

    ctx = tgen.bld

    zmTaskParams = getattr(tgen, 'zm-task-params', {})
    assert zmTaskParams

    cmdArgs = zmTaskParams.get('run', {})
    if not cmdArgs:
        return None

    ruleArgs = cmdArgs.copy()
    cmdType = ruleArgs.pop('$type', '')

    if cmdType != 'func':
        cmd, shell = _processCmdLine(ctx, zmTaskParams)
        ruleArgs['shell'] = shell
        ruleArgs['cmd'] = cmd

    env = tgen.env.derive()
    environ = (env.env or os.environ).copy()
    addRTLibPathsToOSEnv(gatherRtLibPaths(zmTaskParams, env), environ)
    environ.update(ruleArgs.pop('env', {}))
    env.env = environ

    ruleArgs.update({
        'env'   : env,
        'color' : getattr(tgen, 'color', 'BLUE'),
        'cls_keyword' : lambda _: 'Running',
        'cls_str' : lambda _: 'command for task %r' % tgen.name,
    })

    cmd = ruleArgs.pop('cmd', None)

    deepInputs = zmTaskParams.get('deep_inputs', False) or \
                            getattr(tgen, 'deep_inputs', False)
    if deepInputs:
        ruleArgs['deep_inputs'] = True

    if not cmd:
        msg = 'Task %r has not runnable command: %r.' % (tgen.name, cmd)
        raise error.ZenMakeError(msg)

    if cmdType == 'func':
        bconf = ctx.getbconf(tgen.path)
        ruleArgs['rule'] = _createRuleWithFunc(bconf, cmd)
    else:
        ruleArgs['rule'] = cmd

    return ruleArgs

@feature('runcmd')
@after('process_rule', 'apply_link')
def applyRunCmd(tgen):
    """ Apply feature 'runcmd' """

    ruleArgs = _makeCmdRuleArgs(tgen)
    if not ruleArgs:
        return

    # Waf substitutes TGT var from task.outputs but it cannot be used for a task
    # that already has own outputs due to duplication. So it is better to substitute
    # TGT/tgt and SRC/src vars right here.
    cmdline = ruleArgs['rule']
    if isinstance(cmdline, stringtype):
        cwd = ruleArgs['cwd']

        zmTaskParams = getattr(tgen, 'zm-task-params', {})
        target = zmTaskParams.get('target', '')

        source = getattr(tgen, 'source', [])
        source = [ _normpath(_relpath(x.abspath(), cwd)) for x in source]

        substvars = zmTaskParams.get('substvars', {})
        cmdline = substVars(cmdline, substvars.get)

        bvars = ruleArgs['env']['$builtin-vars'].copy()
        bvars.update({ 'src': ' '.join(source), 'tgt': target })
        ruleArgs['rule'] = substBuiltInVars(cmdline, bvars)

    repeat = ruleArgs.pop('repeat', 1)

    cmdTask = None
    if _isCmdStandalone(tgen):
        for k, v in ruleArgs.items():
            setattr(tgen, k, v)
        if getattr(tgen, 'target', None):
            # to avoid problems with spaces in paths
            tgen.target = [tgen.target]
        tgen.process_rule()
        delattr(tgen, 'rule')
        cmdTask = tgen.tasks[0]
    else:
        cmdTask = _createRunCmdTask(tgen, ruleArgs)

    setattr(tgen, 'runcmdTask', cmdTask)

    def wrap(method, task, repeat):
        def execute():
            if repeat == 1:
                return method()
            ret = None
            msg  = "Running #"
            number = 0
            while number < repeat:
                log.info('%s%d' % (msg, number + 1),
                         extra = { 'c1': log.colors(task.color) } )
                ret = method()
                number += 1
            return ret
        return execute

    runcmdTask = tgen.runcmdTask
    runcmdTask.run = wrap(runcmdTask.run, runcmdTask, repeat)

    _fixRunCmdDepsOrder(tgen)
