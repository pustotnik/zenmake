# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module adds Waf feature 'runcmd' in tasks
"""

import os
from waflib.TaskGen import feature, after
from waflib.Errors import WafError
from waflib import Task
from zm.pyutils import viewitems
from zm import log, shared
from zm.waf.addons import postcmd

@postcmd('configure')
def postConf(conf):
    """ Prepare task params after wscript.configure """

    confHandler = shared.buildConfHandler
    bconfPaths  = confHandler.confPaths
    btypeDir    = confHandler.selectedBuildTypeDir
    projectroot = bconfPaths.projectroot
    tasks       = confHandler.tasks

    for taskName, taskParams in viewitems(tasks):
        features = taskParams['features']

        if 'runcmd' not in features:
            continue

        cmdArgs = taskParams.get('run', {})

        cmdTaskArgs = dict(
            name     = taskName,
            shell    = cmdArgs.get('shell', True),
            timeout  = cmdArgs.get('timeout', None),
            env      = cmdArgs.get('env', {}),
            repeat   = cmdArgs.get('repeat', 1),
        )

        cwd = cmdArgs.get('cwd', None)
        if cwd:
            if not os.path.isabs(cwd):
                cwd = os.path.join(projectroot, cwd)
            cwd = conf.root.make_node(cwd).abspath()
        else:
            cwd = btypeDir
        cmdTaskArgs['cwd'] = cwd

        cmdTaskArgs['cmdline'] = cmdline = cmdArgs.get('cmdline', None)
        if cmdline is None:
            cmdEnvVar = taskName.strip().replace('=', '').upper()
            paths = [cwd, projectroot, btypeDir]
            result = conf.find_program(taskName, path_list = paths,
                                       var = cmdEnvVar, quiet = True,
                                       mandatory = False)
            if result:
                cmdTaskArgs['altcmd'] = result[0]

        taskParams['run'] = cmdTaskArgs

def fixRunCmdDepsOrder(tgen):
    """ Fix order of running """

    ctx = tgen.bld
    runcmdTask = getattr(tgen, 'runcmdTask', None)
    assert runcmdTask

    linkTask = getattr(tgen, 'link_task', None)
    if linkTask:
        runcmdTask.set_run_after(linkTask)

    for dep in getattr(tgen, 'use', []):
        try:
            other = ctx.get_tgen_by_name(dep)
        except WafError:
            continue

        # Ensure that the other task generator has created its tasks
        other.post()

        _runcmdTask = getattr(other, 'runcmdTask', None)
        if _runcmdTask:
            runcmdTask.set_run_after(_runcmdTask)
            continue

        linkTask = getattr(other, 'link_task', None)
        if linkTask:
            runcmdTask.set_run_after(linkTask)

def isCmdStandalone(tgen):
    """ Detect is current runcmd standalone """
    features = getattr(tgen, 'features', [])
    otherFeatures = set(features) - set(('runcmd', ))
    return not otherFeatures and not hasattr(tgen, 'rule')

def createRunCmdTask(tgen, ruleArgs):
    """ Create new rule task for runcmd """

    classParams = dict(
        shell = ruleArgs['shell'],
        func  = ruleArgs['rule'],
        color = ruleArgs['color'],
    )

    name = 'command for task %r' % tgen.name
    cls = Task.task_factory(name, **classParams)

    setattr(cls, 'keyword', ruleArgs['cls_keyword'])
    if ruleArgs.get('deep_inputs', False):
        Task.deep_inputs(cls)

    task = tgen.create_task(name)
    for k in ('after', 'before', 'ext_in', 'ext_out'):
        setattr(task, k, ruleArgs.get(k, []))
    for k in ('timeout', 'cwd', 'env'):
        setattr(task, k, ruleArgs[k])

    return task

@feature('runcmd')
@after('process_rule', 'apply_link')
def applyRunCmd(tgen):
    """ Apply feature 'runcmd' """

    ctx = tgen.bld

    zmTaskParams = getattr(tgen, 'zm-task-params', {})
    assert zmTaskParams

    cmdArgs = zmTaskParams.get('run', {})
    if not cmdArgs:
        return

    isStandalone = isCmdStandalone(tgen)

    cmdline = cmdArgs.pop('cmdline', None)
    altcmd = cmdArgs.pop('altcmd', None)
    realTarget = zmTaskParams['$real.target']

    env = ctx.env.derive()
    env.env = dict(env.env or os.environ)
    env.env.update(cmdArgs.pop('env', {}))

    # add new var to use in 'rule'
    env['PROGRAM'] = realTarget

    ruleArgs = cmdArgs.copy()
    ruleArgs.update(dict(
        env   = env,
        color = getattr(tgen, 'color', 'BLUE'),
        cls_keyword = lambda _: 'Running',
    ))
    repeat = ruleArgs.pop('repeat', 1)

    deepInputs = zmTaskParams.get('deep_inputs', False) or \
                            getattr(tgen, 'deep_inputs', False)
    if deepInputs:
        ruleArgs['deep_inputs'] = True

    cmdIsRunnable = False
    if not cmdline:
        cmdline = realTarget
        if not os.path.isfile(cmdline) and altcmd:
            cmdline = altcmd
        cmdIsRunnable = os.path.isfile(cmdline) and \
                                    os.access(cmdline, os.X_OK)
    else:
        cmdIsRunnable = True

    if not cmdIsRunnable:
        log.warn('Task %r has not runnable command line: %r. Skipping.' \
                 % (tgen.name, cmdline))
        return

    ruleArgs['rule'] = cmdline

    if isStandalone:
        for k, v in viewitems(ruleArgs):
            setattr(tgen, k, v)
        if hasattr(tgen, 'target'):
            delattr(tgen, 'target')
        tgen.process_rule()
        delattr(tgen, 'rule')
        setattr(tgen, 'runcmdTask', tgen.tasks[0])
    else:
        task = createRunCmdTask(tgen, ruleArgs)
        setattr(tgen, 'runcmdTask', task)

    def wrap(method, task, repeat):
        def execute():
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

    if repeat > 1:
        runcmdTask = tgen.runcmdTask
        runcmdTask.run = wrap(runcmdTask.run, runcmdTask, repeat)

    fixRunCmdDepsOrder(tgen)
