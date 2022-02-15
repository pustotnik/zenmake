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
from zm import log, cli, error
from zm.autodict import AutoDict as _AutoDict
from zm.features import precmd, postcmd
from zm.edeps import produceExternalDeps
from zm.waf import assist

# This module relies on module 'runcmd'. So module 'runcmd' must be loaded.
# pylint: disable = unused-import
from zm.features import runcmd
# pylint: enable = unused-import

# Command 'test' is always called with the command 'build' in the same
# process. So shared variable can be used to send data
# from the 'build' to the 'test'.
_shared = _AutoDict(

    withTests = False,
    runTestsOnChanges = False,

    # names of test tasks
    testTaskNames = None,

    # queue with names of changed tasks
    changedTasks = deque(),

    # some cached values from build stage
    ctxCache = {},

    testsFound = False,
    testsBuilt = False,
    buildHandled = False,
)

def _wrapNeedToConfigure(_needToConfigure):

    def execute(*args, **kwargs):

        if _needToConfigure(*args, **kwargs):
            return True
        if not _shared.withTests:
            return False

        zmMetaConf = kwargs.get('zmMetaConf', args[0])
        testsConfigured = zmMetaConf.attrs.get('tests-configured', False)
        return not testsConfigured

    execute.__doc__ = _needToConfigure.__doc__
    return execute

assist.needToConfigure = _wrapNeedToConfigure(assist.needToConfigure)

@postcmd('options')
def postOpt(ctx):
    """ Extra init after wscript.options """

    cliArgs = cli.selected.args
    _shared.runTestsOnChanges = False
    if 'runTests' in cliArgs:
        _shared.runTestsOnChanges = cliArgs.runTests == 'on-changes'
    if 'withTests' in cliArgs:
        _shared.withTests = cliArgs.withTests == 'yes'

    # init array of test task names for each bconf
    _shared.testTaskNames = [None] * len(ctx.bconfManager.configs)

@precmd('init', before = ['runcmd'])
def preInit(ctx):
    """ Init before wscript.init """

    cliArgs = cli.selected.args
    if 'buildtype' not in cliArgs:
        return

    testsFound = False
    for idx, bconf in enumerate(ctx.bconfManager.configs):
        tasks = bconf.tasks

        testTaskNames = []
        for name, params in tasks.items():
            features = params['features']

            if 'test' in features:
                testTaskNames.append(name)

        if not testsFound:
            testsFound = bool(testTaskNames)

        assert not _shared.testTaskNames[idx]
        _shared.testTaskNames[idx] = testTaskNames

        if _shared.withTests:
            continue

        # Remove test tasks.
        # It's necessary to do it in 'init' before 'configure'/'build'
        for name in testTaskNames:
            tasks.pop(name, None)

    _shared.testsFound = testsFound

def _isSuitableForRunCmd(taskParams):
    return taskParams['$runnable'] or taskParams.get('run', None)

@postcmd('configure', before = ['runcmd'])
def postConf(conf):
    """ Configure tasks """

    if not _shared.withTests:
        return

    if _shared.withTests and not _shared.testsFound:
        log.warn('There are no tests to configure')
        conf.zmMetaConfAttrs['tests-configured'] = True
        return

    for idx, bconf in enumerate(conf.bconfManager.configs):
        _postConf(bconf, idx)

    conf.zmMetaConfAttrs['tests-configured'] = True

def _postConf(bconf, bconfIndex):

    testTaskNames = _shared.testTaskNames[bconfIndex]
    assert testTaskNames is not None
    if not testTaskNames:
        return

    tasks = bconf.tasks

    for name in testTaskNames:
        params = tasks[name]
        features = params['features']

        # Adding 'runcmd' in the features here forces feature 'runcmd' to
        # handle param 'run' in tasks with 'test'.
        # Even a library can be marked as a test but it cannot be executed
        # and therefore here is selection of tasks to execute by some conditions.
        if _isSuitableForRunCmd(params):
            if 'runcmd' not in features:
                features.append('runcmd')

        params['deep_inputs'] = True

@precmd('build', before = ['runcmd'])
def preBuild(bld):
    """
    Preprocess zm.waf.wscriptimpl.build
    """

    if _shared.withTests and not _shared.testsFound:
        log.warn('There are no tests to build')
        return

    # use tasks from cache db, not from bconf
    tasks = bld.zmtasks
    testTaskNames = []

    _shared.testsBuilt = False
    for params in tasks.values():

        features = params['features']
        if 'test' not in features:
            continue

        # Remove 'runcmd' after command 'configure'. Even though user set
        # 'runcmd' for task with feauture 'test' it doesn't matter.
        # Otherwise all tests will be executed in 'build' command.
        params['features'] = [ x for x in features if x != 'runcmd' ]

        _shared.testsBuilt = True
        testTaskNames.append(params['name'])

    if not _shared.withTests:
        for name in testTaskNames:
            tasks.pop(name, None)
        bld.zmOrdTaskNames = [x for x in bld.zmOrdTaskNames if x not in testTaskNames]

@postcmd('build')
def postBuild(bld):
    """
    Postprocess zm.waf.wscriptimpl.build
    """

    _shared.buildHandled = True

    runTests = False
    if 'runTests' in cli.selected.args:
        runTests = cli.selected.args.runTests
        runTests = runTests and runTests != 'none'
        if runTests and not _shared.testsBuilt:
            log.warn('There are no tests to run')

        runTests = _shared.testsBuilt and runTests

    if not runTests:
        # Prevent running of the 'test' command after the current command by
        # removing of all values 'test' from the list of the current commands.
        from waflib import Options
        Options.commands = [ x for x in Options.commands if x != 'test' ]
        return

    assert _shared.testsBuilt

    for params in bld.zmtasks.values():
        params['$istest'] = 'test' in params['features']

    #Gather some info from BuildContext at the end of the 'build' call.
    #It's just for optimisation.
    ctxCache = _shared.ctxCache
    ctxCache['envs'] = bld.all_envs
    ctxCache['zmtasks'] = bld.zmtasks
    ctxCache['zmdepconfs'] = bld.zmdepconfs
    ctxCache['saved.attrs'] = {}
    for attr in Build.SAVED_ATTRS:
        ctxCache['saved.attrs'][attr] = getattr(bld, attr, {})

@feature('*')
@after('process_rule')
def watchChanges(tgen):
    """
    Watch changes of tasks
    """

    if not _shared.runTestsOnChanges:
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

    if not _shared.withTests:
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

        # pylint: disable = attribute-defined-outside-init
        self.zmtasks = ctxCache['zmtasks']
        self.zmdepconfs = ctxCache['zmdepconfs']

        # clear cache to allow gc to free some memory
        ctxCache.clear()

    def _makeTask(self, taskParams, bconfPaths):
        ctx = self

        notparsedArgs = cli.selected.notparsed
        if notparsedArgs:
            taskParams['run']['extra-args'] = notparsedArgs

        # make task generator suitable for add-on 'runcmd'.
        kwargs = {
            'features' : ['runcmd'],
            'color'    : 'PINK',
        }

        target = taskParams.get('target')
        if target:
            kwargs['name'] = os.path.relpath(target, bconfPaths.startdir)
        else:
            kwargs['name'] = taskParams['name']

        kwargs['zm-task-params'] = taskParams
        ctx(**kwargs)

    def _makeTasks(self):

        # It's already out of build threads now so it's not needed to
        # worry about thread safing of methods

        runTestsOnChanges = _shared.runTestsOnChanges
        ordered = assist.orderTasksByLocalDeps(self.zmtasks)

        changedTasks = set(_shared.changedTasks)

        for taskParams in ordered:
            if not taskParams['$istest']:
                continue
            if not _isSuitableForRunCmd(taskParams):
                continue
            if runTestsOnChanges and taskParams['name'] not in changedTasks:
                continue

            # pylint: disable = no-member
            wspath = self.getStartDirNode(taskParams['$startdir'])
            bconfPaths = self.getbconf(wspath).confPaths
            self._makeTask(taskParams, bconfPaths)

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
            elif task.hasrun == Task.EXCEPTION:
                msg = task.format_error()
                if not log.verbose():
                    # Make a shorter message without a full traceback

                    msgLines = [x for x in msg.splitlines() if x] # remove empty lines
                    msg = ''
                    for line in msgLines:
                        if line.startswith('WafError:'):
                            msg = line[9:].strip()
                            break

                    # last non-empty string contains some message of a python exception
                    msg += '\n  ' + msgLines[-1]
                    msg = "Test %r failed:\n  %s" % (task.name, msg)
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
        produceExternalDeps(self)

        self._makeTasks()
        self._runTasks()
