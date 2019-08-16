# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module adds support for Waf feature 'test' in tasks
"""

import os
import sys
from collections import deque
from waflib.TaskGen import feature, after
from waflib import Build, Task
from waflib.Build import BuildContext
from zm.constants import PLATFORM
from zm.pyutils import viewitems, viewvalues
from zm import log, shared, cli, error
from zm.autodict import AutoDict as _AutoDict

# Command 'test' is always called with the command 'build' in the same
# process at the moment. So shared variable can be used to send data
# from the 'build' to the 'test'.
_shared = _AutoDict(

    #task items to use in 'test' stage
    taskItems = {},

    # queue with names of changed tasks
    changedTasks = deque(),

    # some cached values from build stage
    ctxCache = {},

    testsFound = False,
    buildHandled = False,
)

class TaskItem(object):
    """
    Task info to use in 'test' command.
    """

    def __init__(self, name, params):
        self.name = name
        self.params = params
        self.deps = []

    def weight(self):
        """ Get 'weight' of item. It can be used to sort. """

        _weight = 1
        for dep in self.deps:
            if id(dep) == id(self):
                raise error.ZenMakeError('Dependency cycle found in buildconfig!')
            _weight += dep.weight()
        return _weight

    def __eq__(self, other):
        return self.name == other.name and self.weight() == other.weight()
    def __ne__(self, other):
        return self.name != other.name or self.weight() != other.weight()
    def __lt__(self, other):
        return self.weight() < other.weight()
    def __le__(self, other):
        return self.weight() <= other.weight()
    def __gt__(self, other):
        return self.weight() > other.weight()
    def __ge__(self, other):
        return self.weight() >= other.weight()

def setup():
    """ Some initialization """

    import zm.wscriptimpl

    def wrap(method):
        def execute(bld):
            # only for command 'build'
            if bld.cmd != 'build':
                method(bld)
                return

            preBuild(bld)
            method(bld)
            postBuild(bld)
        return execute

    zm.wscriptimpl.build = wrap(zm.wscriptimpl.build)

def preBuild(bld):
    """
    Preprocess zm.wscriptimpl.build
    """

    from zm.wscriptimpl import validateVariant
    buildtype = validateVariant(bld)

    tasks = bld.env.alltasks[buildtype]

    _shared.testsFound = False
    for taskParams in viewvalues(tasks):

        if 'test' not in taskParams['features']:
            continue

        _shared.testsFound = True
        taskParams['deep_inputs'] = True

    runTests = cli.selected.args.runTests
    runTests = _shared.testsFound and runTests != 'none'
    if runTests:
        processTasksForRun(tasks)

    _shared.buildHandled = True

def processTasksForRun(tasks):
    """
    Order all tasks and collect params for test tasks
    """

    taskItems = _shared.taskItems
    taskItems.clear()

    # Make items
    for name, params in viewitems(tasks):
        _params = {}
        features = params['features']

        _params['test'] = False
        if 'test' in features:
            _params['test'] = True

        runnable = bool([ x for x in features if x.endswith('program') ])
        _params['runnable'] = runnable

        for k in ('name', 'target', 'run', 'use'):
            v = params.get(k, None)
            if v:
                _params[k] = v

        taskItems[name] = TaskItem(name, _params)

    # Make deps
    for name, meta in viewitems(taskItems):
        deps = meta.params.get('use', [])
        for dep in deps:
            other = taskItems.get(dep)
            if other:
                meta.deps.append(other)

def postBuild(bld):
    """
    Gather some info from BuildContext at the end of the 'build' call.
    It's just for optimisation.
    """

    if not _shared.testsFound or cli.selected.args.runTests == 'none':
        # Prevent running of command 'test' after the current command by
        # removing of all values 'test' from list of the current commands.
        from waflib import Options
        Options.commands = [ x for x in Options.commands if x != 'test' ]
        return

    ctxCache = _shared.ctxCache
    ctxCache['envs'] = bld.all_envs
    ctxCache['saved.attrs'] = {}
    for attr in Build.SAVED_ATTRS:
        ctxCache['saved.attrs'][attr] = getattr(bld, attr, {})

@feature('*')
@after('process_rule')
def watchChanges(self):
    """
    Watch changes of tasks
    """

    runTests = cli.selected.args.runTests
    if runTests != 'on-changes':
        return

    def wrap(method, taskName):
        def execute():
            method()
            # deque has fast atomic append() and popleft() operations that
            # do not require locking
            _shared.changedTasks.append(taskName)
        return execute

    for task in self.tasks:
        task.post_run = wrap(task.post_run, self.name)

@feature('test')
@after('apply_link', 'process_use', 'process_rule')
def applyFeatureTest(self):
    """ Some stuff for the feature 'test' """

    # only for command 'build'
    if self.bld.cmd != 'build':
        return

    if cli.selected.args.buildTests == 'yes':
        return

    # Ignore all build tasks for tests in this case
    def alwaysSkip():
        return Task.SKIP_ME
    for task in self.tasks:
        task.runnable_status = alwaysSkip

class TestContext(BuildContext):
    """
    Context for command 'test'
    """

    fun = cmd = 'test'

    def _prepareExecute(self):

        ctxCache = _shared.ctxCache

        if not _shared.buildHandled:
            raise error.ZenMakeLogicError("Build stage is not handled")

        # restore
        bldAttrs = ctxCache.get('saved.attrs', {})
        if not bldAttrs:
            self.restore()
        else:
            for attr in Build.SAVED_ATTRS:
                setattr(self, attr, bldAttrs.get(attr, {}))
            self.init_dirs()

        # load envs
        self.all_envs = ctxCache.get('envs', {})
        if not self.all_envs:
            self.load_envs()

        # clear cache to allow gc to free some memory
        ctxCache.clear()

    def _makeTask(self, taskItem):
        ctx = self
        params = taskItem.params

        bconfPaths = shared.buildConfHandler.confPaths
        target = params.get('target', None)
        if not target:
            return

        runArgs = params.get('run', {})

        kwargs = dict(
            name   = os.path.relpath(target, bconfPaths.projectroot),
            rule   = runArgs.get('cmd', target),
            target = target,
            shell  = runArgs.get('shell', True),
            color  = 'PINK',
        )

        timeout = runArgs.get('timeout', None)
        if timeout is not None:
            kwargs['timeout'] = timeout
            setattr(self, 'timeout', timeout)

        cwd = runArgs.get('cwd', None)
        if cwd:
            if PLATFORM == 'windows':
                cwd.replace('/', os.path.sep)
            if not os.path.isabs(cwd):
                cwd = os.path.join(bconfPaths.projectroot, cwd)
        else:
            cwd = ctx.bldnode
        kwargs['cwd'] = cwd

        tgen = ctx(**kwargs)
        setattr(tgen, 'params', params)

        env = runArgs.get('env', {})
        _env = dict(tgen.env.env or os.environ)
        _env.update(env)
        tgen.env.env = _env

        # add new var to use in 'rule'
        tgen.env['PROGRAM'] = target

    def _makeTasks(self):

        # It's already out of build threads at the moment so no need to
        # worry about thread safing of methods

        runTests = cli.selected.args.runTests
        runTestsOnChanges = runTests == 'on-changes'

        taskItems = _shared.taskItems
        ordered = taskItems.values()
        ordered.sort()

        changedTasks = set(_shared.changedTasks)

        for taskItem in ordered:
            if not taskItem.params['test']:
                continue
            if not taskItem.params['runnable']:
                # Even library can be marked as a test but can not be executed
                continue
            if runTestsOnChanges and taskItem.name not in changedTasks:
                continue

            self._makeTask(taskItem)

        taskItems.clear()

    def _executeTest(self, task):
        tgen = task.generator
        params = tgen.params

        def execute(number = None):
            msg  = "Running test: '%s'" % task.name
            if number is not None:
                msg = '%s (%d)' % (msg, number + 1)
            log.info(msg, extra = { 'c1': log.colors(task.color) } )

            task.process()
            if task.hasrun != Task.SUCCESS:
                if task.hasrun == Task.CRASHED:
                    msg = 'Test %r failed with exit code %r' % (task.name, task.err_code)
                else:
                    msg = task.format_error()
                log.info(msg, extra={'stream':sys.stderr, 'c1': ''})
                return False
            return True

        repeat = params.get('run', {}).get('repeat', None)
        if repeat:
            repeat = int(repeat)
            for num in range(repeat):
                if not execute(num):
                    return False

            return True

        return execute()

    def _runTasks(self):

        # TODO: add parallel running

        def handleTaskGen(tgen):
            if isinstance(tgen, Task.Task):
                tasks = [tgen]
            else:
                tgen.post() # for calls of 'feature' methods, etc.
                tasks = tgen.tasks

            for task in tasks:
                if not self._executeTest(task):
                    return False
            return True

        for group in self.groups:
            for tgen in group:
                if not handleTaskGen(tgen):
                    return

    def execute(self):
        """
        Run command 'test'
        """

        self._prepareExecute()

        log.info("Entering directory `%s'", self.variant_dir)
        self._makeTasks()
        self._runTasks()
        log.info("Leaving directory `%s'", self.variant_dir)
