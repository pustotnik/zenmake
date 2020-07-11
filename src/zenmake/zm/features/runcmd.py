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
from zm.constants import PLATFORM, EXE_FILE_EXTS
from zm.pyutils import viewitems, maptype
from zm import log, error
from zm.utils import cmdHasShellSymbols
from zm.pathutils import PathsParam
from zm.features import postcmd

if PLATFORM == 'windows':
    _CMDFILE_EXTS = EXE_FILE_EXTS + '.py,.pl'
else:
    _CMDFILE_EXTS = EXE_FILE_EXTS

_RE_WITH_TGT = re.compile(r'\$\{*TGT')
_RE_WITH_TARGET = re.compile(r'\$\{*TARGET')

def _processCmdLine(conf, bconf, cwd, shell, cmdArgs):
    """ Get and process 'cmd' at 'configure' stage """

    bconfPaths = bconf.confPaths
    btypeDir   = bconf.selectedBuildTypeDir
    startdir   = bconfPaths.startdir

    cmdline = cmdArgs.get('cmd', '').strip()
    if not cmdline:
        return cmdline, shell

    if not shell:
        shell = cmdHasShellSymbols(cmdline)

    posixMode = os.name == 'posix'
    cmdSplitted = shlex.split(cmdline, posix = posixMode)

    if not shell:
        # Waf can not work correctly with paths with whitespaces when
        # 'shell' is False.
        # TODO: try to make solution for 'shell' == False
        if any(' ' in s for s in cmdSplitted):
            shell = True

    paths = [cwd, startdir, btypeDir]
    paths.extend(os.environ.get('PATH', '').split(os.pathsep))
    fkw = {
        'path_list' : paths, 'quiet' : True,
        'exts' : _CMDFILE_EXTS, 'mandatory' : False
    }

    partsCount = len(cmdSplitted)
    launcher = cmdSplitted[0]
    cmdExt = os.path.splitext(launcher)[1]
    if partsCount == 1 and cmdExt:
        # try to detect interpreter for some cases
        for ext, launcher in ( ('.py', 'python'), ('.pl', 'perl'),):
            if cmdExt != ext:
                continue
            result = conf.find_program(launcher, **fkw)
            if result:
                launcher = result[0]
                cmdline = '%s %s' % (launcher, cmdline)
    elif partsCount > 1 and not shell and not _RE_WITH_TARGET.search(launcher):
        # Waf raises exception in verbose mode with 'shell' == False if it
        # cannot find full path to executable and on windows cmdline
        # like 'python file.py' doesn't work.
        # So here is trying to find full path for such cases.
        result = conf.find_program(launcher, **fkw)
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
        bconf = taskParams['$bconf']
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

        cmdTaskArgs = {
            'name'   : taskParams['name'],
            'timeout': cmdArgs.get('timeout', None),
            'env'    : cmdArgs.get('env', {}),
            'repeat' : cmdArgs.get('repeat', 1),
        }

        cwd = cmdArgs.get('cwd', None)
        if cwd:
            startdir = cmdArgs.get('startdir', bconf.startdir)
            cwd = PathsParam(cwd, startdir, rootdir).abspath()
        else:
            cwd = btypeDir
        cmdTaskArgs['cwd'] = cwd

        # mostly for _processCmdLine
        conf.variant = taskParams['$task.variant']

        cmdTaskArgs['$type'] = ''
        cmd = cmdArgs.get('cmd', None)
        if cmd and callable(cmd):
            # it's needed because a function cannot be saved in a file as is
            cmdTaskArgs['cmd'] = cmd.__name__
            cmdTaskArgs['shell'] = False
            cmdTaskArgs['$type'] = 'func'
        else:
            # By default 'shell' is True to rid of some problems with Waf and Windows
            shell = cmdArgs.get('shell', True)
            cmd, shell = _processCmdLine(conf, bconf, cwd, shell, cmdArgs)
            cmdTaskArgs['shell'] = shell
            cmdTaskArgs['cmd'] = cmd

        taskParams['run'] = cmdTaskArgs

    # switch current env to the root env
    conf.variant = ''

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
    """ Detect is current runcmd standalone """
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
            'target'    : zmTaskParams.get('$real.target', ''),
            'waftask'   : task,
        }
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

    env = tgen.env.derive()
    env.env = (env.env or os.environ).copy()
    env.env.update(ruleArgs.pop('env', {}))

    # add new var to use in 'rule'
    env['TARGET'] = zmTaskParams['$real.target']

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

    if not cmd and zmTaskParams['$runnable']:
        cmd = env['TARGET']

    if not cmd:
        msg = 'Task %r has not runnable command: %r.' % (tgen.name, cmd)
        raise error.ZenMakeError(msg)

    cmdType = ruleArgs.get('$type', '')
    if cmdType == 'func':
        bconf = ctx.getbconf(tgen.path)
        ruleArgs['rule'] = _createRuleWithFunc(bconf, cmd)
    else:
        ruleArgs['rule'] = cmd

    ruleArgs['cmd'] = cmd
    return ruleArgs

@feature('runcmd')
@after('process_rule', 'apply_link')
def applyRunCmd(tgen):
    """ Apply feature 'runcmd' """

    ruleArgs = _makeCmdRuleArgs(tgen)
    if not ruleArgs:
        return

    cmd = ruleArgs.pop('cmd')
    cmdType = ruleArgs.pop('$type', '')
    repeat = ruleArgs.pop('repeat', 1)

    cmdTask = None
    if _isCmdStandalone(tgen):
        for k, v in viewitems(ruleArgs):
            setattr(tgen, k, v)
        if getattr(tgen, 'target', None) is not None:
            if cmdType == 'func' or not _RE_WITH_TGT.search(cmd):
                delattr(tgen, 'target')
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
