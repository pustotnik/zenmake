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
import shlex
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
from zm.features import TASK_TARGET_FEATURES_TO_LANG, TASK_LANG_FEATURES
from zm.features import ToolchainVars
from zm.waf import assist

#pylint: disable=unused-import
# This modules must be just imported
from zm.waf import options, context
#pylint: enable=unused-import

joinpath = os.path.join

CONFTEST_CACHE_FILE = 'conf_check_cache'

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

    if all((not text, not file)):
        msg = "Neither 'text' nor 'file' set in a conf test"
        msg += " with act = 'check-code' for task %r" % taskName
        cfgCtx.fatal(msg)

    if text:
        checkArgs['fragment'] = text
        _confTestCheck(checkArgs, params)

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
        _confTestCheck(checkArgs, params)

def _confTestWriteHeader(checkArgs, params):

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
    if defname:
        checkArgs['define_name'] = defname

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

# TODO: move specific conf tests to the features/

_confTestFuncs = {
    # explicit using of Waf 'check' is disabled
    #'check'               : _confTestCheck,

    # independent
    'check-by-pyfunc'     : _confTestCheckByPyFunc,
    'check-programs'      : _confTestCheckPrograms,
    'parallel'            : _confTestCheckInParallel,
    #
    'check-sys-libs'      : _confTestCheckSysLibs,
    'check-headers'       : _confTestCheckHeaders,
    'check-libs'          : _confTestCheckLibs,
    'check-code'          : _confTestCheckCode,
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

def _genToolAutoName(lang):
    return 'auto-%s' % lang.replace('xx', '++')

TOOL_AUTO_NAMES = { _genToolAutoName(x) for x in ToolchainVars.allLangs() }

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable=no-member,attribute-defined-outside-init

    def __init__(self, *args, **kwargs):
        super(ConfigurationContext, self).__init__(*args, **kwargs)

        self._loadedTools = {}
        self.confChecks = {}
        self.confChecks['cache'] = None
        self.monitFiles = []

        self.validToolchainNames = assist.getValidPreDefinedToolchainNames()

    def _loadTool(self, tool, **kwargs):

        tooldirs = kwargs.get('tooldirs', None)
        withSysPath = kwargs.get('withSysPath', True)
        toolId = kwargs.get('id', '')
        toolId = hash(toolId)

        loadedTool = self._loadedTools.setdefault(tool, {})
        toolInfo = loadedTool.get(toolId)
        if toolInfo:
            # don't load again
            return toolInfo

        module = None
        try:
            module = context.loadTool(tool, tooldirs, withSysPath)
        except ImportError as ex:
            paths = getattr(ex, 'toolsSysPath', sys.path)
            msg = 'Could not load the tool %r' % tool
            msg += ' from %r\n%s' % (paths, ex)
            self.fatal(msg)

        func = getattr(module, 'configure', None)
        if func and callable(func):
            # Here is false-positive of pylint
            # See https://github.com/PyCQA/pylint/issues/1493
            # pylint: disable = not-callable
            func(self)

        if not loadedTool: # avoid duplicates for loading on build stage
            self.tools.append({'tool' : tool, 'tooldir' : tooldirs, 'funs' : None})

        toolenv = self.env
        loadedTool[toolId] = (module, toolenv)

        return module, toolenv

    def _checkToolchainNames(self, bconf):

        # Each bconf has own customToolchains
        customToolchains = bconf.customToolchains
        if customToolchains:
            validNames = self.validToolchainNames.union(customToolchains.keys())
        else:
            validNames = self.validToolchainNames

        for taskName, taskParams in viewitems(bconf.tasks):
            names = taskParams['toolchain']
            for name in names:
                if name not in validNames:
                    msg = 'Toolchain %r for the task %r is not valid.' % (name, taskName)
                    msg += ' Valid toolchains: %r' % list(validNames)
                    raise error.ZenMakeConfError(msg)

    def _loadDetectedToolchain(self, lang, toolId):
        """
        Load auto detected toolchain by its lang
        """

        lang = lang.replace('++', 'xx')
        displayedLang = lang.replace('xx', '++').upper()

        self.msg('Autodetecting toolchain ...', '%s language' % displayedLang)

        cfgVar = ToolchainVars.cfgVarToSetToolchain(lang)

        toolname = None
        toolenv = self.env
        for toolname in toolchains.getNames(lang):
            self.env.stash()
            try:
                # try to load
                toolenv = self.loadTool(toolname, id = toolId)
            except waferror.ConfigurationError:
                self.env.revert()
            else:
                if toolenv[cfgVar]:
                    self.env.commit()
                    break
                self.env.revert()
        else:
            self.fatal('could not configure a %s toolchain!' % displayedLang)

        return toolname, toolenv

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

    def loadTool(self, tool, **kwargs):
        """
        Load tool/toolchain from Waf or another places
        Version of loadTool for configure context.
        """

        startMsg = 'Checking for %r' % tool

        quiet = kwargs.get('quiet', False)
        if quiet:
            try:
                self.in_msg += 1
            except AttributeError:
                self.in_msg = 1

        toolEnv = None
        try:
            try:
                self.start_msg(startMsg)
                toolInfo = self._loadTool(tool, **kwargs)
            except waferror.ConfigurationError as ex:
                self.end_msg(False)
                if 'CXX=g++48' in ex.msg:
                    msg = 'Could not find gcc/g++ (only Clang)'
                    raise waferror.ConfigurationError(msg)
                raise
            else:
                endMsg = True
                toolEnv = toolInfo[1]
                for lang in toolchains.getLangs(tool):
                    var = ToolchainVars.cfgVarToSetToolchain(lang)
                    if toolEnv[var]:
                        endMsg = toolEnv.get_flat(var)
                        break
                self.end_msg(endMsg)
        finally:
            if quiet:
                self.in_msg -= 1

        return toolEnv

    def handleToolchains(self, bconf):
        """
        Handle all toolchains from current build tasks.
        Returns unique names of all toolchains.
        """

        customToolchains = bconf.customToolchains
        toolchainVars = ToolchainVars.allSysVarsToSetToolchain()
        flagVars = ToolchainVars.allSysFlagVars()

        actualToolchains = set(toolchains.getAllNames(withAuto = True))
        # customToolchains can contain unknown custom names
        actualToolchains.update(customToolchains.keys())

        # OS env vars
        osenv = os.environ
        sysEnvToolVars = \
            { var:osenv[var] for var in toolchainVars if var in osenv }
        sysEnvFlagVars = \
            { var:shlex.split(osenv[var]) for var in flagVars if var in osenv}

        for toolchain in tuple(actualToolchains):
            if toolchain in customToolchains and toolchain in TOOL_AUTO_NAMES:
                msg = "Error in the file %r:" % (bconf.path)
                msg += "\n  %r is not valid name" % toolchain
                msg += " in the variable 'toolchains'"
                raise error.ZenMakeConfError(msg)

            settings = customToolchains[toolchain]

            # OS env vars
            settings.vars.update(sysEnvToolVars)
            settings.vars.update(sysEnvFlagVars)
            settings.kind = toolchain if not settings.kind else settings.kind

        toolchainNames = set()

        for taskParams in viewvalues(bconf.tasks):

            features = utils.toList(taskParams.get('features', []))
            _toolchains = []

            # handle env vars to set toolchain
            for var, val in viewitems(sysEnvToolVars):
                lang = ToolchainVars.langBySysVarToSetToolchain(var)
                if not lang or lang not in features:
                    continue
                if val in actualToolchains:
                    # it's lucky value
                    _toolchains.append(val)
                else:
                    # Value from OS env is not name of a toolchain and
                    # therefore it should be set auto-* for toolchain name
                    # ZenMake detects actual name later.
                    _toolchains.append(_genToolAutoName(lang))

            # try to get from the task
            if not _toolchains:
                _toolchains = utils.toList(taskParams.get('toolchain', []))

            if not _toolchains:
                # try to use auto-*
                _toolchains = set()
                for feature in features:
                    lang = TASK_TARGET_FEATURES_TO_LANG.get(feature)
                    if not lang and feature in TASK_LANG_FEATURES:
                        lang = feature
                    if lang:
                        _toolchains.add(_genToolAutoName(lang))
                _toolchains = list(_toolchains)

            toolchainNames.update(_toolchains)

            # store result in task
            taskParams['toolchain'] = _toolchains

        toolchainNames = tuple(toolchainNames)
        return toolchainNames

    def loadToolchains(self, bconf, copyFromEnv):
        """
        Load all selected toolchains
        """

        toolchainNames = self.handleToolchains(bconf)
        self._checkToolchainNames(bconf)

        if not toolchainNames and bconf.tasks:
            log.warn("No toolchains found. Is buildconf correct?")

        toolchainsEnvs = self.zmcache().toolchain.setdefault('envs', {})
        oldEnvName = self.variant
        customToolchains = bconf.customToolchains
        detectedToolNames = {}

        def loadToolchain(toolchain):

            if toolchain in toolchainsEnvs:
                #don't load again
                return

            self.setenv(toolchain, env = copyFromEnv)

            toolId = ''
            toolSettings  = customToolchains[toolchain]

            for var, val in viewitems(toolSettings.vars):
                lang = ToolchainVars.langBySysVarToSetToolchain(var)
                if not lang:
                    # it's not toolchain var
                    continue
                self.env[var] = val
                toolId += '%s=%r ' % (var, val)

            allowedNames = toolchains.getAllNames(withAuto = True)
            if toolSettings.kind not in allowedNames:
                msg = "Error in the file %r:" % (bconf.path)
                msg += "\n  toolchains.%s" % toolchain
                msg += " must have field 'kind' with one of the values: "
                msg += str(allowedNames)[1:-1]
                raise error.ZenMakeConfError(msg)

            # toolchain   - name of a system or custom toolchain
            # toolForLoad - name of module for toolchain
            toolForLoad = toolSettings.kind

            if toolForLoad in TOOL_AUTO_NAMES:
                lang = toolForLoad[5:]
                detectedToolname, toolenv = self._loadDetectedToolchain(lang, toolId)
                detectedToolNames[toolForLoad] = detectedToolname
                if toolchain in TOOL_AUTO_NAMES:
                    toolchainsEnvs[toolchain] = toolenv # to avoid reloading
                    toolchain = detectedToolname
            else:
                toolenv = self.loadTool(toolForLoad, id = toolId)

            toolchainsEnvs[toolchain] = self.env = toolenv

        for name in toolchainNames:
            loadToolchain(name)

        if detectedToolNames:
            # replace all auto-* in build tasks with detected toolchains
            for taskParams in viewvalues(bconf.tasks):
                taskParams['toolchain'] = \
                    [detectedToolNames.get(t, t) for t in taskParams['toolchain']]

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
        fcachedTasks = fcachedTasks.get('all', {})
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
