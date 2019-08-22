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
from zm import shared

def setup():
    """ Some initialization """

    import zm.wscriptimpl

    def wrapConf(method):
        def execute(conf):
            method(conf)
            postConf(conf)
        return execute

    zm.wscriptimpl.configure = wrapConf(zm.wscriptimpl.configure)

def postConf(conf):
    """ Prepare params after wscript.configure """

    confHandler = shared.buildConfHandler
    bconfPaths  = confHandler.confPaths
    btypeDir    = confHandler.selectedBuildTypeDir
    projectroot = bconfPaths.projectroot
    tasks       = confHandler.tasks

    for taskName, taskParams in viewitems(tasks):
        features = taskParams['features']
        assert isinstance(features, list)

        if 'runcmd' not in features:
            continue

        runnable = taskParams['$runnable']
        cmdArgs = taskParams.get('run', {})

        if not cmdArgs and not runnable:
            continue

        cmdTaskArgs = dict(
            name     = taskName,
            shell    = cmdArgs.get('shell', True),
            timeout  = cmdArgs.get('timeout', None),
            env      = cmdArgs.get('env', {}),
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
    if ruleArgs.get('deep_inputs', None):
        Task.deep_inputs(cls)

    task = tgen.create_task(name)
    for k in ('after', 'before', 'ext_in', 'ext_out'):
        setattr(task, k, ruleArgs.get(k, []))
    for k in ('timeout', 'cwd', 'env'):
        setattr(task, k, ruleArgs[k])

    return task

@feature('runcmd')
@after('process_rule', 'apply_link')
def applyRunCmd(self):
    """ Apply feature 'runcmd' """

    ctx = self.bld

    taskParams = getattr(self, 'zm-task-params', {})
    assert taskParams

    cmdArgs = taskParams.get('run', {})
    if not cmdArgs:
        return

    isStandalone = isCmdStandalone(self)

    cmdline = cmdArgs.pop('cmdline', None)
    altcmd = cmdArgs.pop('altcmd', None)
    realTarget = taskParams['$real.target']

    env = ctx.env.derive()
    env.env = dict(env.env or os.environ)
    env.env.update(cmdArgs.pop('env', {}))

    # add new var to use in 'rule'
    env['PROGRAM'] = realTarget

    ruleArgs = cmdArgs
    ruleArgs.update(dict(
        env   = env,
        color = 'BLUE',
        cls_keyword = lambda _: 'Running',
    ))

    if not cmdline:
        cmdline = realTarget
        if not os.path.isfile(cmdline) and altcmd:
            cmdline = altcmd

    ruleArgs['rule'] = cmdline

    if isStandalone:
        for k, v in viewitems(ruleArgs):
            setattr(self, k, v)
        if hasattr(self, 'target'):
            delattr(self, 'target')
        self.process_rule()
        delattr(self, 'rule')
        setattr(self, 'runcmdTask', self.tasks[0])
    else:
        task = createRunCmdTask(self, ruleArgs)
        setattr(self, 'runcmdTask', task)

    fixRunCmdDepsOrder(self)
