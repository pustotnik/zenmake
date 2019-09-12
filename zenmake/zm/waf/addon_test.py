# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module adds Waf feature 'test' in tasks and provides command 'test'.
"""

import os

from collections import deque
from waflib.TaskGen import feature, after
from waflib import Build, Task
from waflib.Build import BuildContext
from zm.pyutils import viewitems, viewvalues
from zm import log, shared, cli, error
from zm.autodict import AutoDict as _AutoDict
from zm.waf.addons import precmd, postcmd

# Command 'test' is always called with the command 'build' in the same
# process. So shared variable can be used to send data
# from the 'build' to the 'test'.
_shared = _AutoDict(

    buildTests = False,
    runTestsOnChanges = False,

    # tasks from buildconf
    confTasks = None,

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

    __slots__ = ('name', 'params', 'deps')

    def __init__(self, name, params):
        self.name = name
        self.params = params
        self.deps = []

    def weight(self):
        """ Get 'weight' of item. It can be used to sort. """

        if not self.deps:
            return 1

        for dep in self.deps:
            if id(dep) == id(self):
                raise error.ZenMakeError('Dependency cycle found in buildconfig!')

        return 1 + max([dep.weight() for dep in self.deps])

    def __eq__(self, other):
        return (self.weight() == other.weight()) and (self.name == other.name)
    def __ne__(self, other):
        return not self.__eq__(other)
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

    _shared.runTestsOnChanges = cli.selected.args.runTests == 'on-changes'
    _shared.buildTests = cli.selected.args.buildTests

def _isSuitableForRunCmd(taskParams):
    return taskParams['$runnable'] or taskParams.get('run', None)

@postcmd('configure', beforeAddOn = ['runcmd'])
def postConf(_):
    """ Configure tasks """

    confHandler = shared.buildConfHandler
    tasks       = confHandler.tasks

    for params in viewvalues(tasks):
        features = params['features']

        if 'test' not in features:
            continue

        assert isinstance(features, list)
        # Adding 'runcmd' in the features here forces add-on 'runcmd' to
        # handle param 'run' in tasks with 'test'.
        # Even library can be marked as a test but it can not be executed
        # and therefore here is selection of tasks to execute by some conditions.
        if _isSuitableForRunCmd(params):
            if 'runcmd' not in features:
                features.append('runcmd')

        params['deep_inputs'] = True

@precmd('build', beforeAddOn = ['runcmd'])
def preBuild(bld):
    """
    Preprocess zm.wscriptimpl.build
    """

    # only for command 'build'
    if bld.cmd != 'build':
        return

    from zm.wscriptimpl import validateVariant
    buildtype = validateVariant(bld)

    tasks = bld.env.alltasks[buildtype]
    _shared.confTasks = tasks.copy()
    _shared.testsFound = False
    ignoredBuildTasks = []
    for name, params in viewitems(tasks):

        features = params['features']
        if 'test' not in features:
            continue

        # Remove 'runcmd' after command 'configure'. Even though user set
        # 'runcmd' for task with feauture 'test' it doesn't matter.
        # Otherwise all tests will be executed in 'build' command.
        params['features'] = [ x for x in features if x != 'runcmd' ]

        if not _shared.buildTests:
            ignoredBuildTasks.append(name)

        _shared.testsFound = True

    for k in ignoredBuildTasks:
        tasks.pop(k, None)

@postcmd('build')
def postBuild(bld):
    """
    Gather some info from BuildContext at the end of the 'build' call.
    It's just for optimisation.
    """

    # only for command 'build'
    if bld.cmd != 'build':
        return

    _shared.buildHandled = True

    runTests = cli.selected.args.runTests
    runTests = _shared.testsFound and runTests != 'none'

    if not runTests:
        # Prevent running of command 'test' after the current command by
        # removing of all values 'test' from the list of the current commands.
        from waflib import Options
        Options.commands = [ x for x in Options.commands if x != 'test' ]
        return

    processTasksForRun(_shared.confTasks)

    ctxCache = _shared.ctxCache
    ctxCache['envs'] = bld.all_envs
    ctxCache['saved.attrs'] = {}
    for attr in Build.SAVED_ATTRS:
        ctxCache['saved.attrs'][attr] = getattr(bld, attr, {})

def processTasksForRun(tasks):
    """
    Order all tasks and collect params for test tasks
    """

    taskItems = _shared.taskItems
    taskItems.clear()

    # Make items
    for name, params in viewitems(tasks):
        params['$istest'] = 'test' in params['features']
        taskItems[name] = TaskItem(name, params)

    # Make deps
    for name, meta in viewitems(taskItems):
        deps = meta.params.get('use', [])
        for dep in deps:
            other = taskItems.get(dep)
            if other:
                meta.deps.append(other)

@feature('*')
@after('process_rule')
def watchChanges(tgen):
    """
    Watch changes of tasks
    """

    if not _shared.runTestsOnChanges:
        return

    # only for command 'build'
    if tgen.bld.cmd != 'build':
        return

    def wrap(method, taskName):
        def execute():
            method()
            # deque has fast atomic append() and popleft() operations that
            # do not require locking
            _shared.changedTasks.append(taskName)
        return execute

    for task in tgen.tasks:
        task.post_run = wrap(task.post_run, tgen.name)

@feature('test')
@after('apply_link', 'process_use', 'process_rule')
def applyFeatureTest(tgen):
    """ Some stuff for the feature 'test' """

    # only for command 'build'
    if tgen.bld.cmd != 'build':
        return

    if not _shared.buildTests:
        # Ignore all build tasks for tests in this case
        for task in tgen.tasks:
            task.runnable_status = lambda: Task.SKIP_ME

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

        # make task generator suitable for add-on 'runcmd'.
        kwargs = dict(
            features = ['runcmd'],
            name     = os.path.relpath(target, bconfPaths.projectroot),
            color    = 'PINK',
            run      = params.get('run', {}),
        )

        kwargs['zm-task-params'] = params
        ctx(**kwargs)

    def _makeTasks(self):

        # It's already out of build threads now so it's not needed to
        # worry about thread safing of methods

        runTestsOnChanges = _shared.runTestsOnChanges

        taskItems = _shared.taskItems
        ordered = sorted(taskItems.values())

        changedTasks = set(_shared.changedTasks)

        for taskItem in ordered:
            if not taskItem.params['$istest']:
                continue
            if not _isSuitableForRunCmd(taskItem.params):
                continue
            if runTestsOnChanges and taskItem.name not in changedTasks:
                continue

            self._makeTask(taskItem)

        taskItems.clear()

    def _executeTest(self, task):

        msg  = "Running test: '%s'" % task.name
        log.info(msg, extra = { 'c1': log.colors(task.color) } )

        if not os.path.isdir(task.cwd):
            msg = "Test cannot be run because "
            msg += "there's no such directory for 'cwd': %r" % task.cwd
            raise error.ZenMakeError(msg)

        task.process()
        if task.hasrun != Task.SUCCESS:
            if task.hasrun == Task.CRASHED:
                msg = 'Test %r failed with exit code %r' % (task.name, task.err_code)
            else:
                msg = task.format_error()
            raise error.ZenMakeError(msg)

    def _runTasks(self):

        def tgpost(tgen):
            try:
                post = tgen.post
            except AttributeError:
                pass
            else:
                post()

        # for calls of 'feature' methods, etc.
        for group in self.groups:
            for tgen in group:
                tgpost(tgen)

        while True:
            alltasks = []
            for group in self.groups:
                for tgen in group:
                    tasks = [tgen] if isinstance(tgen, Task.Task) else tgen.tasks
                    tasks = [ x for x in tasks if not x.hasrun ]
                    alltasks.extend(tasks)
            if not alltasks:
                break

            for task in alltasks:
                self._executeTest(task)

    def execute(self):
        """
        Run command 'test'
        """

        self._prepareExecute()

        log.info("Entering directory `%s'", self.variant_dir)
        try:
            self._makeTasks()
            self._runTasks()
        finally:
            log.info("Leaving directory `%s'", self.variant_dir)
