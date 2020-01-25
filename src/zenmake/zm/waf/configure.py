# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some portions derived from Thomas Nagy's Waf code
 Waf is Copyright (c) 2005-2019 Thomas Nagy

"""

import os
import shutil
import traceback

# NOTICE:This module must import modules with original Waf context classes
# before declaring their alter implementions.
# Otherwise classes in this module can be ignored. In normal case of
# using of the Waf such classes are created in the 'wscript' because this
# file is loaded always after all Waf context classes.

from waflib import ConfigSet, Task, Options
from waflib.Utils import SIG_NIL
from waflib.Context import Context as WafContext, create_context as createContext
from waflib.Configure import ConfigurationContext as WafConfContext, conf
from waflib import Errors as waferror
from waflib.Tools.c_config import DEFKEYS
from zm.constants import CONFTEST_DIR_PREFIX
from zm.autodict import AutoDict as _AutoDict
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm import utils, log, toolchains, error
from zm.waf import assist

joinpath = os.path.join

CONFTEST_CACHE_FILE = 'conf_check_cache'

CONFTEST_HASH_USED_ENV_KEYS = set(
    ('DEST_BINFMT', 'DEST_CPU', 'DEST_OS')
)
for _var in toolchains.CompilersInfo.allVarsToSetCompiler():
    CONFTEST_HASH_USED_ENV_KEYS.add(_var)
    CONFTEST_HASH_USED_ENV_KEYS.add('%s_VERSION' % _var)
    CONFTEST_HASH_USED_ENV_KEYS.add('%s_NAME' % _var)

CONFTEST_HASH_IGNORED_FUNC_ARGS = set(
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
    checkCache = cfgCtx.confChecks['cache']['checks'][checkHash]

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

class CfgCheckTask(Task.Task):
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

def _applyParallelTasksDeps(tasks):

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
                raise error.ZenMakeConfError('No test named %r' % key)
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

@conf
def checkInParallel(self, checkArgsList, **kwargs):
    """
    Runs configuration tests in parallel.
    Results are printed sequentially at the end.
    """

    from waflib import Runner

    self.start_msg('Checking in parallel %d tests' % len(checkArgsList))

    # Force a copy so that threads append to the same list at least
    # no order is guaranteed, but the values should not disappear at least
    for var in ('DEFINES', DEFKEYS):
        self.env.append_value(var, [])
    self.env.DEFINE_COMMENTS = self.env.DEFINE_COMMENTS or {}

    tasks = []
    runnerCtx = _RunnerBldCtx(tasks)

    tryall = kwargs.get('tryall', False)

    for i, args in enumerate(checkArgsList):
        args['$parallel-id'] = i

        checkTask = CfgCheckTask(env = None)
        checkTask.stopRunnerOnError = not tryall
        checkTask.conf = self
        checkTask.bld = runnerCtx # to use in task.log_display(task.generator.bld)

        # bind a logger that will keep the info in memory
        checkTask.logger = log.makeMemLogger(str(id(checkTask)), self.logger)

        checkTask.call = dict( name = args.pop('$func-name'), args = args)

        tasks.append(checkTask)

    _applyParallelTasksDeps(tasks)

    def getTasksGenerator():
        yield tasks
        while 1:
            yield []

    runnerCtx.producer = scheduler = Runner.Parallel(runnerCtx, Options.options.jobs)
    scheduler.biter = getTasksGenerator()

    self.end_msg('started')
    try:
        scheduler.start()
    except waferror.WafError as ex:
        if ex.msg.startswith('Task dependency cycle'):
            msg = "Infinite recursion was detected in parallel tests."
            msg += " Check all parameters 'before' and 'after'."
            raise error.ZenMakeConfError(msg)
        # it's a different error
        raise

    # flush the logs in order into the config.log
    for tsk in tasks:
        tsk.logger.memhandler.flush()

    self.start_msg('-> processing test results')

    for tsk in scheduler.error:
        if not getattr(tsk, 'err_msg', None):
            continue
        self.to_log(tsk.err_msg)
        self.end_msg('fail', color = 'RED')
        msg = 'There is an error in the Waf, read config.log for more information'
        raise waferror.WafError(msg)

    okStates = (Task.SUCCESS, Task.NOT_RUN)
    failureCount = len([x for x in tasks if x.hasrun not in okStates])

    if failureCount:
        self.end_msg('%s test(s) failed' % failureCount, color = 'YELLOW')
    else:
        self.end_msg('all ok')

    for tsk in tasks:
        # in rare case we get "No handlers could be found for logger"
        log.freeLogger(tsk.logger)

        if tsk.hasrun not in okStates and tsk.call['args'].get('mandatory', True):
            self.fatal('One of the tests has failed, read config.log for more information')

def _loadConfCheckCache(cfgCtx):
    """
    Load cache data for conf checks.
    """

    cachePath = joinpath(cfgCtx.cachedir.abspath(), CONFTEST_CACHE_FILE)
    try:
        cache = ConfigSet.ConfigSet(cachePath)
    except EnvironmentError:
        cache = ConfigSet.ConfigSet()

    if 'checks' not in cache:
        cache['checks'] = {}
    checks = cache['checks']

    # reset all but not 'id'
    for v in viewvalues(checks):
        if isinstance(v, maptype):
            _new = { 'id' : v['id']}
            v.clear()
            v.update(_new)

    return cache

def _getConfCheckCache(cfgCtx, checkHash):
    """
    Get conf check cache by hash
    """

    cache = cfgCtx.confChecks['cache']
    if cache is None:
        cfgCtx.confChecks['cache'] = cache = _loadConfCheckCache(cfgCtx)

    checks = cache['checks']
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
    hashVals['toolchain'] = taskParams.get('toolchain', '')

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

    return utils.hexOfStr(utils.hashOfStrs(buff))

@conf
def checkByPyFunc(self, **kwargs):
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
        import sys
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

def _confTestCheckByPyFunc(checkArgs, params):

    # pylint: disable = deprecated-method, broad-except

    import inspect

    cfgCtx    = params['cfgCtx']
    buildtype = params['buildtype']
    taskName  = params['taskName']

    checkArgs = checkArgs.copy()

    func = checkArgs['func']
    try:
        argsSpec = inspect.getfullargspec(func)
    except AttributeError:
        argsSpec = inspect.getargspec(func)

    noFuncArgs = not any(argsSpec[0:3])
    args = dict(task = taskName, buildtype = buildtype)

    checkArgs['args'] = None if noFuncArgs else args
    checkArgs['msg'] = 'Checking by function %r' % func.__name__

    parallelChecks = params.get('parallel-checks', None)

    if parallelChecks is not None:
        # checkArgs is shared so it can be changed later
        checkArgs['$func-name'] = 'checkByPyFunc'
        parallelChecks.append(checkArgs)
    else:
        cfgCtx.checkByPyFunc(**checkArgs)

def _confTestCheckPrograms(checkArgs, params):
    cfgCtx = params['cfgCtx']

    cfgCtx.setenv('')

    names = utils.toList(checkArgs.pop('names', []))
    checkArgs['path_list'] = utils.toList(checkArgs.pop('paths', []))

    for name in names:
        # Method find_program caches result in the cfgCtx.env and
        # therefore it's not needed to cache it here.
        cfgCtx.find_program(name, **checkArgs)

def _confTestCheckSysLibs(checkArgs, params):
    taskParams = params['taskParams']

    sysLibs = utils.toList(taskParams.get('sys-libs', []))
    sysLibs.extend(utils.toList(taskParams.get('lib', [])))
    checkArgs['names'] = sysLibs
    _confTestCheckLibs(checkArgs, params)

def _confTestCheckLibs(checkArgs, params):
    libs = utils.toList(checkArgs.pop('names', []))
    autodefine = checkArgs.pop('autodefine', False)
    for lib in libs:
        _checkArgs = checkArgs.copy()
        _checkArgs['msg'] = 'Checking for library %s' % lib
        _checkArgs['lib'] = lib
        if autodefine and 'define_name' not in _checkArgs:
            _checkArgs['define_name'] = 'HAVE_LIB_' + lib.upper()
        _confTestCheck(_checkArgs, params)

def _confTestCheckHeaders(checkArgs, params):
    headers = utils.toList(checkArgs.pop('names', []))
    for header in headers:
        checkArgs['msg'] = 'Checking for header %s' % header
        checkArgs['header_name'] = header
        _confTestCheck(checkArgs, params)

def _confTestCheckCode(checkArgs, params):

    cfgCtx = params['cfgCtx']
    taskName = params['taskName']

    msg = 'Checking code snippet'
    label = checkArgs.pop('label', None)
    if label is not None:
        msg += " %r" % label

    checkArgs['msg'] = msg

    text = checkArgs.pop('text', None)
    file = checkArgs.pop('file', None)

    if all((text is None, file is None)):
        msg = "Neither 'text' nor 'file' exists in a conf test"
        msg += " with act = 'check-code' for task %r" % taskName
        cfgCtx.fatal(msg)

    if text is not None:
        checkArgs['fragment'] = text
        _confTestCheck(checkArgs, params)

    if file is not None:
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
        _confTestCheck(checkArgs, params)

def _confTestWriteHeader(checkArgs, params):

    buildtype  = params['buildtype']
    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    def defaultFileName():
        return utils.normalizeForFileName(taskName).lower()

    fileName = checkArgs.pop('file', '%s_%s' %
                             (defaultFileName(), 'config.h'))
    fileName = joinpath(buildtype, fileName)
    projectName = cfgCtx.getbconf().projectName or ''
    guardname = utils.normalizeForDefine(projectName + '_' + fileName)
    checkArgs['guard'] = checkArgs.pop('guard', guardname)
    # write the configuration header from the build directory
    checkArgs['top'] = True

    cfgCtx.write_config_header(fileName, **checkArgs)

def _confTestCheck(checkArgs, params):
    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    # _confTestCheck is used in loops so it's needed to save checkArgs
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
    if defname is not None:
        checkArgs['define_name'] = defname

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

def _confTestCheckInParallel(checkArgs, params):
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
        'check-sys-libs', 'check-headers',
        'check-libs', 'check-by-pyfunc', 'check-code',
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

    params = dict(
        msg = 'Checking in parallel',
    )
    params.update(checkArgs)

    cfgCtx.checkInParallel(parallelCheckArgsList, **params)

_confTestFuncs = {
    'check-by-pyfunc'     : _confTestCheckByPyFunc,
    'check-programs'      : _confTestCheckPrograms,
    'check-sys-libs'      : _confTestCheckSysLibs,
    'check-headers'       : _confTestCheckHeaders,
    'check-libs'          : _confTestCheckLibs,
    'check-code'          : _confTestCheckCode,
    # explicit using of Waf 'check' is disabled
    #'check'               : _confTestCheck,
    'parallel'            : _confTestCheckInParallel,
    'write-config-header' : _confTestWriteHeader,
}

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

        func = _confTestFuncs.get(act)
        if not func:
            msg = "Unknown act %r in the configuration test %r for task %r!" \
                    % (act, checkArgs, taskName)
            ctx.fatal(msg)

        func(checkArgs, params)

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable=no-member,attribute-defined-outside-init

    def __init__(self, *args, **kwargs):
        super(ConfigurationContext, self).__init__(*args, **kwargs)

        self.confChecks = {}
        self.confChecks['cache'] = None
        self.monitFiles = []

    def _loadDetectedCompiler(self, lang):
        """
        Load auto detected compiler by its lang
        """

        compilers = toolchains.CompilersInfo.compilers(lang)
        envVar    = toolchains.CompilersInfo.varToSetCompiler(lang)

        for compiler in compilers:
            self.env.stash()
            self.start_msg('Checking for %r' % compiler)
            try:
                self.load(compiler)
            except waferror.ConfigurationError:
                self.env.revert()
                self.end_msg(False)
            else:
                if self.env[envVar]:
                    self.end_msg(self.env.get_flat(envVar))
                    self.env.commit()
                    break
                self.env.revert()
                self.end_msg(False)
        else:
            self.fatal('could not configure a %s compiler!' % lang.upper())

    # override
    def execute(self):

        # See details here: https://gitlab.com/ita1024/waf/issues/1563
        self.env.NO_LOCK_IN_RUN = True
        self.env.NO_LOCK_IN_TOP = True

        super(ConfigurationContext, self).execute()

        self.monitFiles.extend([x.path for x in self.bconfManager.configs])
        filePath = self.bconfManager.root.confPaths.zmcmnconfset
        assist.dumpZenMakeCmnConfSet(self.monitFiles, filePath)

        cache = self.confChecks['cache']
        if cache is not None:
            cachePath = joinpath(self.cachedir.abspath(), CONFTEST_CACHE_FILE)
            cache.store(cachePath)

    # override
    def post_recurse(self, node):
        # Avoid some actions from WafConfContext.post_recurse.
        # It's mostly for performance.
        WafContext.post_recurse(self, node)

    def setDirectEnv(self, name, env):
        """ Set env without deriving and other actions """

        self.variant = name
        self.all_envs[name] = env

    def loadToolchains(self, bconf, copyFromEnv):
        """
        Load all selected toolchains
        """

        if not bconf.toolchainNames and bconf.tasks:
            log.warn("No toolchains found. Is buildconf correct?")

        toolchainsEnvs = self.zmcache().toolchain.setdefault('envs', {})
        oldEnvName = self.variant

        def loadToolchain(toolchain):
            toolname = toolchain
            if toolname in toolchainsEnvs:
                #don't load again
                return

            self.setenv(toolname, env = copyFromEnv)
            custom  = bconf.customToolchains.get(toolname, None)
            if custom is not None:
                for var, val in viewitems(custom.vars):
                    self.env[var] = val
                toolchain = custom.kind

            if toolchain.startswith('auto-'):
                lang = toolchain[5:]
                self._loadDetectedCompiler(lang)
            else:
                self.load(toolchain)
            toolchainsEnvs[toolname] = self.env

        for toolchain in bconf.toolchainNames:
            loadToolchain(toolchain)

        # switch to old env due to calls of 'loadToolchain'
        self.setenv(oldEnvName)

        return toolchainsEnvs

    def saveTasksInEnv(self, bconf):
        """
        Merge current tasks with existing tasks and tasks from cache file
        and save them in the root env.
        """

        # root env
        env = self.all_envs['']

        if 'zmtasks' not in env:
            env.zmtasks = _AutoDict()

        cache = self.zmcache()
        if 'fcachetasks' in cache:
            fcachedTasks = cache['fcachetasks']
        else:
            fcachedTasks = self.loadTasksFromFileCache(bconf.confPaths.wafcachefile)
            cache['fcachetasks'] = fcachedTasks

        # merge with tasks from file cache
        for btype, tasks in viewitems(fcachedTasks):
            btypeTasks = env.zmtasks.all[btype]
            btypeTasks.update(tasks)

        # merge with existing tasks
        buildtype = bconf.selectedBuildType
        btypeTasks = env.zmtasks.all[buildtype]
        btypeTasks.update(bconf.tasks)

    def makeTaskEnv(self, taskVariant):
        """
        Create env for task from root env with cleanup
        """

        # make deep copy to rid of side effects with different flags
        # in different tasks
        taskEnv = assist.deepcopyEnv(self.all_envs.pop(taskVariant))

        assert 'zmtasks' not in taskEnv
        return taskEnv

    def addExtraMonitFiles(self, bconf):
        """
        Add extra file paths to monitor for autoconfig feature
        """

        files = bconf.features.get('monitor-files', [])
        if not files:
            return

        files = utils.toList(files)
        startdir = bconf.confPaths.startdir
        for file in files:
            file = utils.getNativePath(file)
            path = joinpath(startdir, file)
            if not os.path.isfile(path):
                msg = "Error in the file %r:\n" % bconf.path
                msg += "File path %r " % file
                msg += "from the features.monitor-files doesn't exist"
                if not os.path.abspath(file):
                    msg += " in the directory %r" % startdir
                self.fatal(msg)
            self.monitFiles.append(path)

    def runConfTests(self, buildtype, tasks):
        """
        Run supported configuration tests/checks
        """

        for taskName, taskParams in viewitems(tasks):
            confTests = taskParams.get('conftests', [])
            if not confTests:
                continue
            log.info('.. Checks for the %r:' % taskName)
            params = dict(
                cfgCtx = self,
                buildtype = buildtype,
                taskName = taskName,
                taskParams = taskParams,
            )
            _handleConfChecks(confTests, params)

        self.setenv('')

    def configureTaskParams(self, bconf, taskParams):
        """
        Handle every known task param that can be handled at configure stage.
        It is better for common performance because command 'configure' is used
        rarely than command 'build'.
        """

        btypeDir = bconf.selectedBuildTypeDir
        rootdir  = bconf.rootdir
        startdir = bconf.startdir
        taskName = taskParams['name']

        assist.detectConfTaskFeatures(taskParams)
        assist.validateConfTaskFeatures(taskParams, self.validUserTaskFeatures)
        features = taskParams['features']

        normalizeTarget = taskParams.get('normalize-target-name', False)
        target = taskParams.get('target', taskName)
        if normalizeTarget:
            target = utils.normalizeForFileName(target, spaceAsDash = True)
        targetPath = joinpath(btypeDir, target)

        assist.handleTaskIncludesParam(taskParams, rootdir, startdir)
        assist.handleTaskLibPathParam(taskParams, rootdir, startdir)
        assist.handleTaskExportDefinesParam(taskParams)

        kwargs = dict(
            name     = taskName,
            target   = targetPath,
            #counter for the object file extension
            idx      = taskParams.get('object-file-counter', 1),
        )

        nameMap = (
            ('sys-libs','lib', 'tolist'),
            ('rpath','rpath', 'tolist'),
            ('use', 'use', 'tolist'),
            ('includes', 'includes', None),
            ('libpath', 'libpath', None),
            ('ver-num', 'vnum', None),
            ('export-includes', 'export_includes', None),
            ('export-defines', 'export_defines', None),
            ('install-path', 'install_path', None),
        )
        for param in nameMap:
            zmKey = param[0]
            if zmKey in taskParams:
                wafKey, toList = param[1], param[2] == 'tolist'
                if toList:
                    kwargs[wafKey] = utils.toList(taskParams[zmKey])
                else:
                    kwargs[wafKey] = taskParams[zmKey]
                if zmKey != wafKey:
                    del taskParams[zmKey]

        # set of used keys in kwargs must be included in set from getUsedWafTaskKeys()
        assert set(kwargs.keys()) <= assist.getUsedWafTaskKeys()

        taskParams.update(kwargs)

        prjver = bconf.projectVersion
        if prjver and 'vnum' not in taskParams:
            taskParams['vnum'] = prjver

        taskVariant = taskParams['$task.variant']
        taskEnv = self.all_envs[taskVariant]

        runnable = False
        realTarget = targetPath
        for feature in features:
            pattern = taskEnv[feature + '_PATTERN']
            if pattern:
                realTarget = joinpath(btypeDir, pattern % target)
            if feature.endswith('program'):
                runnable = True

        taskParams['$real.target'] = realTarget
        taskParams['$runnable'] = runnable
