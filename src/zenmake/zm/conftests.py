# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some portions derived from Thomas Nagy's Waf code
 Waf is Copyright (c) 2005-2019 Thomas Nagy

"""

import os
import sys
import shutil
import traceback
import inspect

from waflib import Task, Options
from waflib.Utils import SIG_NIL
from waflib.Context import create_context as createContext
from waflib.Configure import ConfigurationContext as WafConfContext, conf
from waflib import Errors as waferror
from waflib.Tools.c_config import DEFKEYS
from zm.constants import CONFTEST_DIR_PREFIX
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm import utils, log, error
from zm.features import ToolchainVars, TASK_TARGET_FEATURES_TO_LANG

joinpath = os.path.join

try:
    inspectArgSpec = inspect.getfullargspec
except AttributeError:
    inspectArgSpec = inspect.getargspec

CONFTEST_HASH_USED_ENV_KEYS = set(
    ('DEST_BINFMT', 'DEST_CPU', 'DEST_OS')
)
for _var in ToolchainVars.allCfgVarsToSetToolchain():
    CONFTEST_HASH_USED_ENV_KEYS.add(_var)
    CONFTEST_HASH_USED_ENV_KEYS.add('%s_VERSION' % _var)
    CONFTEST_HASH_USED_ENV_KEYS.add('%s_NAME' % _var)

CONFTEST_HASH_IGNORED_FUNC_ARGS = frozenset(
    ('mandatory', 'msg', 'okmsg', 'errmsg', 'id', 'before', 'after')
)

def _makeRunBuildBldCtx(ctx, checkArgs, topdir, bdir):

    bld = createContext('build', top_dir = topdir, out_dir = bdir)

    # avoid unnecessary directory
    bld.variant = ''

    bld.init_dirs()
    bld.progress_bar = 0
    bld.targets = '*'

    bld.logger = ctx.logger
    bld.all_envs.update(ctx.all_envs)
    bld.env = checkArgs['env']

    # for function 'build_fun' only
    bld.kw = checkArgs
    bld.conf = ctx # it's used for bld.conf.to_log

    return bld

@conf
def run_build(self, *k, **checkArgs):
    """
    Create a temporary build context to execute a build.
    It's alternative version of the waflib.Configure.run_build and it can be
    used only in ZenMake.
    """

    # pylint: disable = invalid-name,unused-argument

    cfgCtx = self if isinstance(self, WafConfContext) else self.cfgCtx

    # this function can not be called from conf.multicheck
    assert not hasattr(self, 'multicheck_task')

    checkHash = checkArgs['$conf-test-hash']
    checkCache = cfgCtx.getConfCache()['conf-checks'][checkHash]

    retval = checkCache['retval']
    if retval is not None:
        if isinstance(retval, stringtype) and retval.startswith('Conf test failed'):
            self.fatal(retval)
        return retval

    checkId = str(checkCache['id'])
    if '$parallel-id' in checkArgs:
        checkId = '%s.%s' % (checkId, checkArgs['$parallel-id'])

    topdir = cfgCtx.bldnode.abspath() + os.sep
    topdir += '%s%s' % (CONFTEST_DIR_PREFIX, checkId)

    if os.path.exists(topdir):
        shutil.rmtree(topdir)

    try:
        os.makedirs(topdir)
    except OSError:
        pass

    try:
        os.stat(topdir)
    except OSError:
        self.fatal('cannot use the configuration test folder %r' % topdir)

    bdir = joinpath(topdir, 'b')
    if not os.path.exists(bdir):
        os.makedirs(bdir)

    self.test_bld = bld = _makeRunBuildBldCtx(self, checkArgs, topdir, bdir)

    checkArgs['build_fun'](bld)
    ret = -1

    try:
        try:
            bld.compile()
        except waferror.WafError:
            # TODO: add more info?
            tsk = bld.producer.error[0]
            errDetails = "\n[CODE]\n%s" % bld.kw['code']
            errDetails += "\n[LAST COMMAND]\n%s" % tsk.last_cmd
            ret = 'Conf test failed: %s' % errDetails

            self.fatal(ret)
        else:
            ret = getattr(bld, 'retval', 0)
    finally:
        shutil.rmtree(topdir)
        checkCache['retval'] = ret

    return ret

class _CfgCheckTask(Task.Task):
    """
    A task that executes build configuration tests (calls conf.check).
    It's used to run conf checks in parallel.
    """

    def __init__(self, *args, **kwargs):
        Task.Task.__init__(self, *args, **kwargs)

        self.stopRunnerOnError = True
        self.conf = None
        self.bld = None
        self.logger = None
        self.call = None

    def display(self):
        return ''

    def runnable_status(self):
        for task in self.run_after:
            if not task.hasrun:
                return Task.ASK_LATER
        return Task.RUN_ME

    def uid(self):
        return SIG_NIL

    def signature(self):
        return SIG_NIL

    def run(self):
        """ Run task """

        # pylint: disable = broad-except

        cfgCtx = self.conf
        topdir = cfgCtx.srcnode.abspath()
        bdir = cfgCtx.bldnode.abspath()
        bld = createContext('build', top_dir = topdir, out_dir = bdir)

        bld.variant = '' # avoid unnecessary directory
        bld.env = cfgCtx.env
        bld.init_dirs()
        bld.in_msg = 1 # suppress top-level start_msg
        bld.logger = self.logger
        bld.cfgCtx = cfgCtx

        args = self.call['args']
        func = getattr(bld, self.call['name'])

        mandatory = args.get('mandatory', True)
        args['mandatory'] = True
        retval = 0
        try:
            func(**args)
        except Exception:
            retval = 1
        finally:
            args['mandatory'] = mandatory

        if retval != 0 and mandatory and self.stopRunnerOnError:
            # say 'stop' to runner
            self.bld.producer.stop = True

        return retval

    def process(self):

        Task.Task.process(self)

        args = self.call['args']
        if 'msg' not in args:
            return

        with self.generator.bld.cmnLock:
            self.conf.start_msg(args['msg'])
            if self.hasrun == Task.NOT_RUN:
                self.conf.end_msg('test cancelled', 'YELLOW')
            elif self.hasrun != Task.SUCCESS:
                self.conf.end_msg(args.get('errmsg', 'no'), 'YELLOW')
            else:
                self.conf.end_msg(args.get('okmsg', 'yes'), 'GREEN')

class _RunnerBldCtx(object):
    """
    A class that is used as BuildContext to execute conf tests in parallel
    """

    # pylint: disable = invalid-name, missing-docstring

    def __init__(self, tasks):

        # Keep running all tasks until all tasks not processed
        # and self.producer.stop == False
        self.keep = True

        self.task_sigs = {}
        self.imp_sigs = {}
        self.progress_bar = 0
        self.producer = None
        self.cmnLock = utils.threading.Lock()
        self._tasks = tasks

    def total(self):
        return len(self._tasks)

    def to_log(self, *k, **kw):
        # pylint: disable = unused-argument
        return

def _applyParallelTasksDeps(tasks, bconfpath):

    idToTask = {}
    for tsk in tasks:
        args = tsk.call['args']
        if 'id' in args:
            idToTask[args['id']] = tsk

    def applyDeps(idToTask, task, before):
        tasks = task.call['args'].get('before' if before else 'after', [])
        for key in utils.toList(tasks):
            otherTask = idToTask.get(key, None)
            if not otherTask:
                msg = 'No test named %r' % key
                raise error.ZenMakeConfError(msg, confpath = bconfpath)
            if before:
                otherTask.run_after.add(task)
            else:
                task.run_after.add(otherTask)

    # second pass to set dependencies with after/before
    for tsk in tasks:
        applyDeps(idToTask, tsk, before = True)
        applyDeps(idToTask, tsk, before = False)

    # remove 'before' and 'after' from args to avoid matching with the same
    # parameters for Waf Task.Task
    for tsk in tasks:
        args = tsk.call['args']
        args.pop('before', None)
        args.pop('after', None)

def _checkInParallelImpl(cfgCtx, checkArgsList, **kwargs):
    """
    Runs configuration tests in parallel.
    Results are printed sequentially at the end.
    """

    from waflib import Runner

    cfgCtx.start_msg('Checking in parallel %d tests' % len(checkArgsList))

    # Force a copy so that threads append to the same list at least
    # no order is guaranteed, but the values should not disappear at least
    for var in ('DEFINES', DEFKEYS):
        cfgCtx.env.append_value(var, [])
    cfgCtx.env.DEFINE_COMMENTS = cfgCtx.env.DEFINE_COMMENTS or {}

    tasks = []
    runnerCtx = _RunnerBldCtx(tasks)

    tryall = kwargs.get('tryall', False)

    for i, args in enumerate(checkArgsList):
        args['$parallel-id'] = i

        checkTask = _CfgCheckTask(env = None)
        checkTask.stopRunnerOnError = not tryall
        checkTask.conf = cfgCtx
        checkTask.bld = runnerCtx # to use in task.log_display(task.generator.bld)

        # bind a logger that will keep the info in memory
        checkTask.logger = log.makeMemLogger(str(id(checkTask)), cfgCtx.logger)

        checkTask.call = { 'name' : args.pop('$func-name'), 'args' : args }

        tasks.append(checkTask)

    bconf = cfgCtx.getbconf()
    bconfpath = bconf.path

    _applyParallelTasksDeps(tasks, bconfpath)

    def getTasksGenerator():
        yield tasks
        while 1:
            yield []

    runnerCtx.producer = scheduler = Runner.Parallel(runnerCtx, Options.options.jobs)
    scheduler.biter = getTasksGenerator()

    cfgCtx.end_msg('started')
    try:
        scheduler.start()
    except waferror.WafError as ex:
        if ex.msg.startswith('Task dependency cycle'):
            msg = "Infinite recursion was detected in parallel tests."
            msg += " Check all parameters 'before' and 'after'."
            raise error.ZenMakeConfError(msg, confpath = bconfpath)
        # it's a different error
        raise

    # flush the logs in order into the config.log
    for tsk in tasks:
        tsk.logger.memhandler.flush()

    cfgCtx.start_msg('-> processing test results')

    for tsk in scheduler.error:
        if not getattr(tsk, 'err_msg', None):
            continue
        cfgCtx.to_log(tsk.err_msg)
        cfgCtx.end_msg('fail', color = 'RED')
        msg = 'There is an error in the Waf, read config.log for more information'
        raise waferror.WafError(msg)

    okStates = (Task.SUCCESS, Task.NOT_RUN)
    failureCount = len([x for x in tasks if x.hasrun not in okStates])

    if failureCount:
        cfgCtx.end_msg('%s test(s) failed' % failureCount, color = 'YELLOW')
    else:
        cfgCtx.end_msg('all ok')

    for tsk in tasks:
        # in rare case we get "No handlers could be found for logger"
        log.freeLogger(tsk.logger)

        if tsk.hasrun not in okStates and tsk.call['args'].get('mandatory', True):
            cfgCtx.fatal('One of the tests has failed, read config.log for more information')

def _loadConfCheckCache(cache):
    """
    Load cache data for conf checks.
    """

    if 'conf-checks' not in cache:
        cache['conf-checks'] = {}
    checks = cache['conf-checks']

    # reset all but not 'id'
    for v in viewvalues(checks):
        if isinstance(v, maptype):
            _new = { 'id' : v['id']}
            v.clear()
            v.update(_new)

    return checks

def _getConfCheckCache(cfgCtx, checkHash):
    """
    Get conf check cache by hash
    """

    cache = cfgCtx.getConfCache()
    if 'conf-checks' not in cache:
        _loadConfCheckCache(cache)
    checks = cache['conf-checks']

    if checkHash not in checks:
        lastId = checks.get('last-id', 0)
        checks['last-id'] = currentId = lastId + 1
        checks[checkHash] = {}
        checks[checkHash]['id'] = currentId

    return checks[checkHash]

def _calcConfCheckHexHash(checkArgs, params):

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    hashVals = {}
    for k, v in viewitems(checkArgs):
        if k in CONFTEST_HASH_IGNORED_FUNC_ARGS or k[0] == '$':
            continue
        hashVals[k] = v
    # just in case
    hashVals['toolchain'] = utils.toList(taskParams.get('toolchain', []))

    buff = [ '%s: %s' % (k, str(hashVals[k])) for k in sorted(hashVals.keys()) ]

    env = cfgCtx.env
    envStr = ''
    for k in sorted(env.keys()):
        if k not in CONFTEST_HASH_USED_ENV_KEYS:
            # these keys are not significant for hash but can make cache misses
            continue
        val = env[k]
        envStr += '%r %r ' % (k, val)
    buff.append('%s: %s' % ('env', envStr))

    return utils.hexOfStr(utils.hashObj(buff))

@conf
def runCheckByPyFunc(self, **kwargs):
    """
    Run configuration test by python function
    """

    # pylint: disable = broad-except

    func = kwargs['func']
    args = kwargs['args']

    self.start_msg(kwargs['msg'])

    withException = False
    try:
        if args:
            result = func(**args)
        else:
            result = func()
    except Exception:
        result = False
        withException = True

    if result:
        self.end_msg('yes')
        return

    self.end_msg(result = 'no', color = 'YELLOW')

    msg = "\nChecking by function %r failed: " % func.__name__

    if withException:
        excInfo = sys.exc_info()
        stack = traceback.extract_tb(excInfo[2])[-1::]
        msg += "\n%s: %s\n" % (excInfo[0].__name__, excInfo[1])
        msg += "".join(traceback.format_list(stack))
    else:
        msg += "function returned %s" % str(result)

    if log.verbose() > 1:
        # save to log and raise exception
        self.fatal(msg)

    try:
        # save to log but don't allow exception
        self.fatal(msg)
    except waferror.ConfigurationError:
        pass

    self.fatal('The configuration failed')

def checkByPyFunc(checkArgs, params):
    """ Check by python function """

    # pylint: disable = deprecated-method, broad-except

    cfgCtx    = params['cfgCtx']
    buildtype = params['buildtype']
    taskName  = params['taskName']

    checkArgs = checkArgs.copy()

    func = checkArgs['func']
    argsSpec = inspectArgSpec(func)
    noFuncArgs = not any(argsSpec[0:3])
    args = { 'task' : taskName, 'buildtype' : buildtype }

    checkArgs['args'] = None if noFuncArgs else args
    checkArgs['msg'] = 'Checking by function %r' % func.__name__

    parallelChecks = params.get('parallel-checks', None)

    if parallelChecks is not None:
        # checkArgs is shared so it can be changed later
        checkArgs['$func-name'] = 'runCheckByPyFunc'
        parallelChecks.append(checkArgs)
    else:
        cfgCtx.runCheckByPyFunc(**checkArgs)

def checkPrograms(checkArgs, params):
    """ Check programs """

    cfgCtx = params['cfgCtx']

    cfgCtx.setenv('')

    names = utils.toList(checkArgs.pop('names', []))
    checkArgs['path_list'] = utils.toList(checkArgs.pop('paths', []))

    for name in names:
        # Method find_program caches result in the cfgCtx.env and
        # therefore it's not needed to cache it here.
        cfgCtx.find_program(name, **checkArgs)

def checkLibs(checkArgs, params):
    """ Check shared libraries """

    autodefine = checkArgs.pop('autodefine', False)

    libs = []
    if checkArgs.pop('fromtask', True):
        taskParams = params['taskParams']
        libs.extend(utils.toList(taskParams.get('libs', [])))
        libs.extend(utils.toList(taskParams.get('lib', [])))
    libs.extend(utils.toList(checkArgs.pop('names', [])))
    libs = utils.uniqueListWithOrder(libs)

    for lib in libs:
        _checkArgs = checkArgs.copy()
        _checkArgs['msg'] = 'Checking for library %s' % lib
        _checkArgs['lib'] = lib
        if autodefine and 'define_name' not in _checkArgs:
            _checkArgs['define_name'] = 'HAVE_LIB_' + lib.upper()
        checkWithBuild(_checkArgs, params)

def checkHeaders(checkArgs, params):
    """ Check headers """

    headers = utils.toList(checkArgs.pop('names', []))
    for header in headers:
        checkArgs['msg'] = 'Checking for header %s' % header
        checkArgs['header_name'] = header
        checkWithBuild(checkArgs, params)

def checkCode(checkArgs, params):
    """ Check code snippet """

    cfgCtx = params['cfgCtx']
    taskName = params['taskName']

    msg = 'Checking code snippet'
    label = checkArgs.pop('label', None)
    if label is not None:
        msg += " %r" % label

    checkArgs['msg'] = msg

    text = checkArgs.pop('text', None)
    file = checkArgs.pop('file', None)

    if all((not text, not file)):
        msg = "Neither 'text' nor 'file' set in a conf test"
        msg += " with act = 'check-code' for task %r" % taskName
        cfgCtx.fatal(msg)

    if text:
        checkArgs['fragment'] = text
        checkWithBuild(checkArgs, params)

    if file:
        bconf = cfgCtx.getbconf()
        startdir = bconf.confPaths.startdir
        file = utils.getNativePath(file)
        path = joinpath(startdir, file)
        if not os.path.isfile(path):
            msg = "Error in declaration of a conf test "
            msg += "with act = 'check-code' for task %r:" % taskName
            msg += "\nFile %r doesn't exist" % file
            if not os.path.abspath(file):
                msg += " in the directory %r" % startdir
            cfgCtx.fatal(msg)

        cfgCtx.monitFiles.append(path)

        with open(path, 'r') as file:
            text = file.read()

        checkArgs['fragment'] = text
        checkWithBuild(checkArgs, params)

def writeConfigHeader(checkArgs, params):
    """ write config header """

    buildtype  = params['buildtype']
    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    def defaultFileName():
        return utils.normalizeForFileName(taskName).lower()

    fileName = checkArgs.pop('file', None)
    if not fileName:
        fileName = '%s_%s' % (defaultFileName(), 'config.h')
    fileName = joinpath(buildtype, fileName)

    guardname = checkArgs.pop('guard', None)
    if not guardname:
        projectName = cfgCtx.getbconf().projectName or ''
        guardname = utils.normalizeForDefine(projectName + '_' + fileName)
    checkArgs['guard'] = guardname

    # write the configuration header from the build directory
    checkArgs['top'] = True

    cfgCtx.write_config_header(fileName, **checkArgs)

def checkWithBuild(checkArgs, params):
    """
    Check it with building of some code.
    It's general function for many checks.
    """

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    # checkWithBuild is used in loops so it's needed to save checkArgs
    # without changes
    checkArgs = checkArgs.copy()

    hexHash = _calcConfCheckHexHash(checkArgs, params)
    checkCache = _getConfCheckCache(cfgCtx, hexHash)
    if 'retval' not in checkCache:
        # to use it without lock in threads we need to insert this key
        checkCache['retval'] = None
    checkArgs['$conf-test-hash'] = hexHash

    #TODO: add as option
    # if it is False then write-config-header doesn't write defines
    #checkArgs['global_define'] = False

    defname = checkArgs.pop('defname', None)
    if defname:
        checkArgs['define_name'] = defname

    codeType = checkArgs.pop('code-type', None)
    if codeType:
        checkArgs['compiler'] = checkArgs['compile_mode'] = codeType
        checkArgs['type'] = '%sprogram' % codeType

    compileFilename = checkArgs.pop('compile-filename', None)
    if compileFilename:
        checkArgs['compile_filename'] = compileFilename

    defines = checkArgs.pop('defines', None)
    if defines:
        checkArgs['defines'] = utils.toList(defines)

    libpath = taskParams.get('libpath', None)
    if libpath:
        checkArgs['libpath'] = libpath

    includes = taskParams.get('includes', None)
    if includes:
        checkArgs['includes'] = includes

    parallelChecks = params.get('parallel-checks', None)

    if parallelChecks is not None:
        # checkArgs is shared so it can be changed later
        checkArgs['$func-name'] = 'check'
        parallelChecks.append(checkArgs)
    else:
        cfgCtx.check(**checkArgs)

def checkInParallel(checkArgs, params):
    """
    Run checks in parallel
    """

    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    subchecks = checkArgs.pop('checks', [])
    if not subchecks:
        msg = "No checks for act 'parallel' in conftests for task %r" % taskName
        log.warn(msg)
        return

    supportedActs = (
        'check-headers', 'check-libs', 'check-by-pyfunc', 'check-code',
    )

    parallelCheckArgsList = []
    params['parallel-checks'] = parallelCheckArgsList

    for check in subchecks:
        errMsg = None
        if isinstance(check, maptype):
            act = check.get('act')
            if not act:
                errMsg = "Parameter 'act' not found in parallel test '%r'" % check
            elif act not in supportedActs:
                errMsg = "act %r can not be used inside the act 'parallel'" % act
                errMsg += " for conftests in task %r!" % taskName
        elif callable(check):
            pass
        else:
            errMsg = "Test '%r' is not supported." % check

        if errMsg:
            cfgCtx.fatal(errMsg)

    _handleConfChecks(subchecks, params)
    params.pop('parallel-checks', None)

    if not parallelCheckArgsList:
        return

    for args in parallelCheckArgsList:
        args['msg'] = "  %s" % args['msg']

    params = {
        'msg' : 'Checking in parallel',
    }
    params.update(checkArgs)

    _checkInParallelImpl(cfgCtx, parallelCheckArgsList, **params)

_commonConfTestsFuncs = {
    'check-by-pyfunc' : checkByPyFunc,
    'check-programs'  : checkPrograms,
    'parallel'        : checkInParallel,
}

_confTestsTable = { x:_commonConfTestsFuncs.copy() for x in ToolchainVars.allLangs()}

def _handleConfChecks(checks, params):

    for checkArgs in checks:
        if callable(checkArgs):
            checkArgs = {
                'act' : 'check-by-pyfunc',
                'func' : checkArgs,
            }
        else:
            # checkArgs is changed in conf test func below
            checkArgs = checkArgs.copy()

        ctx = params['cfgCtx']
        taskName = params['taskName']

        act = checkArgs.pop('act', None)
        if act is None:
            msg = "No act in the configuration test %r for task %r!" \
                    % (checkArgs, taskName)
            ctx.fatal(msg)

        lang = None
        features = params['taskParams']['features']
        for feature in features:
            lang = TASK_TARGET_FEATURES_TO_LANG.get(feature)
            if lang:
                break

        table = _confTestsTable.get(lang, _commonConfTestsFuncs)
        func = table.get(act)
        if not func:
            msg = "Unsupported act %r in the configuration test %r for task %r!" \
                    % (act, checkArgs, taskName)
            ctx.fatal(msg)

        func(checkArgs, params)

def regConfTestFuncs(lang, funcs):
    """
    Register functions for configuration tests
    """

    _confTestsTable[lang].update(funcs)

def handleConfTests(checks, params):
    """
    Handle configuration tests
    """

    _handleConfChecks(checks, params)
