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
import re
import shutil
import traceback
import inspect

from waflib import Task, Options, Runner
from waflib.Utils import SIG_NIL
from waflib.Context import create_context as createContext
from waflib.Configure import ConfigurationContext as WafConfContext, conf
from waflib import Errors as waferror
from waflib.Tools.c_config import DEFKEYS
from zm.constants import CONFTEST_DIR_PREFIX
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm.autodict import AutoDict as _AutoDict
from zm import utils, log, error
from zm.pathutils import getNativePath
from zm.features import ToolchainVars

joinpath = os.path.join

_RE_PKGCONFIG_PKGS = re.compile(r"(\S+)(\s*(?:[<>]|=|[<>]\s*=)\s*[^\s<>=]+)?")

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

def cfgmandatory(func):
    """
    Handle a parameter named 'mandatory' to disable the configuration errors
    """

    def decorator(*args, **kwargs):
        mandatory = kwargs.pop('mandatory', True)
        try:
            return func(*args, **kwargs)
        except waferror.ConfigurationError:
            if mandatory:
                raise

    return decorator

def _findProgram(cfgCtx, filename, **kwargs):

    envName = cfgCtx.variant
    # set root env for cache
    cfgCtx.variant = ''

    if 'path_list' not in kwargs:
        kwargs['path_list'] = utils.toList(kwargs.pop('paths', []))

    # Method find_program caches result in the cfgCtx.env and
    # therefore it's not needed to cache it here.

    result = None
    try:
        result = cfgCtx.find_program(filename, **kwargs)
    finally:
        cfgCtx.variant = envName

    if result:
        result = ' '.join(result)
    return result

class _LockWrapper(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        if self.lock is not None:
            return self.lock.__enter__()
        return None

    def __exit__(self, _type, value, _traceback):
        if self.lock is not None:
            self.lock.__exit__(_type, value, _traceback)

def _makeRunBuildBldCtx(ctx, args, topdir, bdir):

    bld = createContext('build', top_dir = topdir, out_dir = bdir)

    # avoid unnecessary directories
    bld.buildWorkDirName = bld.variant = ''

    bld.init_dirs()
    bld.progress_bar = 0
    bld.targets = '*'

    bld.logger = ctx.logger
    bld.all_envs.update(ctx.all_envs)
    bld.env = args['env']

    # for function 'build_fun' only
    bld.kw = args
    bld.conf = ctx # it's used for bld.conf.to_log

    return bld

def _runCheckBuild(self, **checkArgs):
    """
    It's alternative implementation for the waflib.Configure.run_build.
    This method must be thread safe.
    """

    cfgCtx = self if isinstance(self, WafConfContext) else self.cfgCtx

    # WARN:
    # Any method from cfgCtx that is used here must be thread safe

    # this function can not be called from conf.multicheck
    assert getattr(self, 'multicheck_task', None) is None

    checkHash = checkArgs['$conf-test-hash']
    checkCache = cfgCtx.getConfCache()['config-actions'][checkHash]

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

    bld = _makeRunBuildBldCtx(self, checkArgs, topdir, bdir)

    checkArgs['build_fun'](bld)
    retval = -1

    try:
        try:
            bld.compile()
        except waferror.WafError:
            # TODO: add more info?
            tsk = bld.producer.error[0]
            errDetails = "\n[CODE]\n%s" % bld.kw['code']
            errDetails += "\n[LAST COMMAND]\n%s" % tsk.last_cmd
            retval = 'Conf test failed: %s' % errDetails

            self.fatal(retval)
        else:
            retval = getattr(bld, 'retval', 0)
    finally:
        shutil.rmtree(topdir)
        checkCache['retval'] = retval

    return retval

@conf
def check(self, *args, **kwargs):
    """
    It's alternative version of the waflib.Tools.c_config.check and it can be
    used only in ZenMake. Original 'check' from waf doesn't have good thread
    safity and sometimes it leads to problems with defines. So here is stable
    solution with mutex locks. This solution doesn't have noticeable
    performance penalty because only 'validate_c' and 'post_check' are locked.
    """

    locker = _LockWrapper(kwargs.pop('lock', None))

    with locker:
        self.validate_c(kwargs)

    self.startMsg(kwargs['msg'], **kwargs)
    result = None
    try:
        # _runCheckBuild is thread safe
        result = _runCheckBuild(self, **kwargs)
    except waferror.ConfigurationError:
        self.endMsg(kwargs['errmsg'], 'YELLOW', **kwargs)
        if log.verbose() > 1:
            raise
        self.fatal('The configuration failed')
    else:
        kwargs['success'] = result

    with locker:
        result = self.post_check(*args, **kwargs)

    if not result:
        self.endMsg(kwargs['errmsg'], 'YELLOW', **kwargs)
        self.fatal('The configuration failed %r' % result)
    else:
        self.endMsg(kwargs['okmsg'], **kwargs)
    return result

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

        # avoid unnecessary directories
        bld.buildWorkDirName = bld.variant = ''
        bld.env = cfgCtx.env
        bld.init_dirs()
        bld.in_msg = 1 # suppress top-level startMsg
        bld.logger = self.logger
        bld.cfgCtx = cfgCtx

        args = self.call['args']
        func = getattr(bld, self.call['name'])

        args['lock'] = self.generator.bld.cmnLock

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
            self.conf.startMsg(args['msg'])
            if self.hasrun == Task.NOT_RUN:
                self.conf.endMsg('cancelled', color = 'YELLOW')
            elif self.hasrun != Task.SUCCESS:
                self.conf.endMsg(args.get('errmsg', 'no'), color = 'YELLOW')
            else:
                self.conf.endMsg(args.get('okmsg', 'yes'), color = 'GREEN')

class _RunnerBldCtx(object):
    """
    A class that is used as BuildContext to execute conf tests in parallel
    """

    # pylint: disable = invalid-name, missing-docstring

    def __init__(self, tasks):

        # Keep running all tasks while all tasks will not be not processed
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
                msg = 'No config action named %r' % key
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

def _runActionsInParallelImpl(params, actionArgsList, **kwargs):
    """
    Runs configuration actions in parallel.
    Results are printed sequentially at the end.
    """

    cfgCtx = params['cfgCtx']
    bconf  = params['bconf']

    cfgCtx.startMsg('Paralleling %d actions' % len(actionArgsList))

    # Force a copy so that threads append to the same list at least
    for var in ('DEFINES', DEFKEYS):
        cfgCtx.env.append_value(var, [])
    cfgCtx.env.DEFINE_COMMENTS = cfgCtx.env.DEFINE_COMMENTS or {}

    tasks = []
    runnerCtx = _RunnerBldCtx(tasks)

    tryall = kwargs.get('tryall', False)

    for i, args in enumerate(actionArgsList):
        args['$parallel-id'] = i

        checkTask = _CfgCheckTask(env = None)
        checkTask.stopRunnerOnError = not tryall
        checkTask.conf = cfgCtx
        checkTask.bld = runnerCtx # to use in task.log_display(task.generator.bld)

        # bind a logger that will keep the info in memory
        checkTask.logger = log.makeMemLogger(str(id(checkTask)), cfgCtx.logger)

        checkTask.call = { 'name' : args.pop('$func-name'), 'args' : args }

        tasks.append(checkTask)

    bconfpath = bconf.path

    _applyParallelTasksDeps(tasks, bconfpath)

    def getTasksGenerator():
        yield tasks
        while 1:
            yield []

    runnerCtx.producer = scheduler = Runner.Parallel(runnerCtx, Options.options.jobs)
    scheduler.biter = getTasksGenerator()

    cfgCtx.endMsg('started')
    try:
        scheduler.start()
    except waferror.WafError as ex:
        if ex.msg.startswith('Task dependency cycle'):
            msg = "Infinite recursion was detected in parallel config actions."
            msg += " Check all parameters 'before' and 'after'."
            raise error.ZenMakeConfError(msg, confpath = bconfpath)
        # it's a different error
        raise

    # flush the logs in order into the config.log
    for tsk in tasks:
        tsk.logger.memhandler.flush()

    cfgCtx.startMsg('-> processing results')

    for tsk in scheduler.error:
        if not getattr(tsk, 'err_msg', None):
            continue
        cfgCtx.to_log(tsk.err_msg)
        cfgCtx.endMsg('fail', color = 'RED')
        msg = 'There is an error in the Waf, read config.log for more information'
        raise waferror.WafError(msg)

    okStates = (Task.SUCCESS, Task.NOT_RUN)
    failureCount = len([x for x in tasks if x.hasrun not in okStates])

    if failureCount:
        cfgCtx.endMsg('%s failed' % failureCount, color = 'YELLOW')
    else:
        cfgCtx.endMsg('all ok')

    for tsk in tasks:
        # in rare case we get "No handlers could be found for logger"
        log.freeLogger(tsk.logger)

        if tsk.hasrun not in okStates and tsk.call['args'].get('mandatory', True):
            cfgCtx.fatal('One of the actions has failed, read config.log for more information')

def _handleLoadedActionsCache(cache):
    """
    Handle loaded cache data for config actions.
    """

    if 'config-actions' not in cache:
        cache['config-actions'] = {}
    actions = cache['config-actions']

    # reset all but not 'id'
    for v in viewvalues(actions):
        if isinstance(v, maptype):
            _new = { 'id' : v['id']}
            v.clear()
            v.update(_new)

    return actions

def _getConfActionCache(cfgCtx, actionHash):
    """
    Get conf action cache by hash
    """

    cache = cfgCtx.getConfCache()
    if 'config-actions' not in cache:
        _handleLoadedActionsCache(cache)
    actions = cache['config-actions']

    if actionHash not in actions:
        lastId = actions.get('last-id', 0)
        actions['last-id'] = currentId = lastId + 1
        actions[actionHash] = {}
        actions[actionHash]['id'] = currentId

    return actions[actionHash]

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
def runPyFuncAsAction(self, **kwargs):
    """
    Run python function as an action
    """

    # pylint: disable = broad-except

    func = kwargs['func']
    args = kwargs['args']

    self.startMsg(kwargs['msg'])

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
        self.endMsg('yes')
        return

    self.endMsg('no', color = 'YELLOW')

    msg = "\nConfig function %r failed: " % func.__name__

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

def callPyFunc(actionArgs, params):
    """ Make or prepare python function as an action """

    cfgCtx    = params['cfgCtx']
    buildtype = params['buildtype']
    taskName  = params['taskName']

    actionArgs = actionArgs.copy()

    func = actionArgs['func']
    argsSpec = inspectArgSpec(func)
    noFuncArgs = not any(argsSpec[0:3])
    args = { 'task' : taskName, 'buildtype' : buildtype }

    actionArgs['args'] = None if noFuncArgs else args
    actionArgs['msg'] = 'Function %r' % func.__name__

    parallelActions = params.get('parallel-actions', None)

    if parallelActions is not None:
        # actionArgs is shared so it can be changed later
        actionArgs['$func-name'] = 'runPyFuncAsAction'
        parallelActions.append(actionArgs)
    else:
        cfgCtx.runPyFuncAsAction(**actionArgs)

def checkPrograms(checkArgs, params):
    """ Check programs """

    cfgCtx = params['cfgCtx']

    names = utils.toList(checkArgs.pop('names', []))
    checkArgs['path_list'] = utils.toList(checkArgs.pop('paths', []))

    for name in names:
        _findProgram(cfgCtx, name, **checkArgs)

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
        _checkWithBuild(_checkArgs, params)

def checkHeaders(checkArgs, params):
    """ Check headers """

    headers = utils.toList(checkArgs.pop('names', []))
    for header in headers:
        checkArgs['msg'] = 'Checking for header %s' % header
        checkArgs['header_name'] = header
        _checkWithBuild(checkArgs, params)

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
        msg = "Neither 'text' nor 'file' set in a config action"
        msg += " 'check-code' for task %r" % taskName
        cfgCtx.fatal(msg)

    if text:
        checkArgs['fragment'] = text
        _checkWithBuild(checkArgs, params)

    if file:
        startdir = params['bconf'].confPaths.startdir
        file = getNativePath(file)
        path = joinpath(startdir, file)
        if not os.path.isfile(path):
            msg = "Error in declaration of a config action "
            msg += "'check-code' for task %r:" % taskName
            msg += "\nFile %r doesn't exist" % file
            if not os.path.abspath(file):
                msg += " in the directory %r" % startdir
            cfgCtx.fatal(msg)

        cfgCtx.monitFiles.append(path)

        with open(path, 'r') as file:
            text = file.read()

        checkArgs['fragment'] = text
        _checkWithBuild(checkArgs, params)

def _checkWithBuild(checkArgs, params):
    """
    Check it with building of some code.
    It's general function for many checks.
    """

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    # _checkWithBuild is used in loops so it's needed to save checkArgs
    # without changes
    checkArgs = checkArgs.copy()

    hexHash = _calcConfCheckHexHash(checkArgs, params)
    checkCache = _getConfActionCache(cfgCtx, hexHash)
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

    parallelActions = params.get('parallel-actions', None)

    if parallelActions is not None:
        # checkArgs is shared so it can be changed later
        checkArgs['$func-name'] = 'check'
        parallelActions.append(checkArgs)
    else:
        cfgCtx.check(**checkArgs)

def _parsePkgConfigPackages(packages, confpath):

    result = []

    packageGroups = _RE_PKGCONFIG_PKGS.findall(packages)
    # remove all whitespaces
    packageGroups = [ ( x[0], ''.join(x[1].split()) ) for x in packageGroups]

    def raiseInvalidPackages(packages, confpath):
        msg = "The value %r is invalid for the parameter 'packages'" % packages
        msg += " in config action 'pkgconfig'"
        raise error.ZenMakeConfError(msg, confpath = confpath)

    pkgInfo = _AutoDict()
    pkgSeen = set()
    for name, verline in packageGroups:
        if any(x in name for x in ('<', '>', '=')):
            raiseInvalidPackages(packages, confpath)

        pkgItem = pkgInfo[name]
        pkgItem.name = name

        pkgItem.setdefault('uselib', name)
        pkgItem.setdefault('cmdline', [])
        cmdarg = name

        if verline:
            if len(verline) < 2 or not any(verline[0] == x for x in ('<', '>', '=')):
                raiseInvalidPackages(packages, confpath)
            index = 1
            if verline[1] == '=':
                index = 2
            cmdarg += " %s %s" % (verline[0:index], verline[index:])

            _verline = verline.replace('<', 'l').replace('>', 'g').replace('=', 'e')
            pkgItem.uselib += '_%s' % _verline

        pkgItem.cmdline.append(cmdarg)

        if name not in pkgSeen:
            result.append(pkgItem)
            pkgSeen.add(name)

    for item in result:
        item.uselib = utils.normalizeForDefine(item.uselib)

    return result

@cfgmandatory
def _runToolConfig(cfgCtx, **kwargs):
    """
    Run ``pkg-config`` or other ``-config`` applications and parse result
    """

    cmd = [kwargs['runpath']]
    cmd += kwargs['cmd-args']

    parseFlags = kwargs.get('parse-flags', False)

    cfgCtx.startMsg(kwargs['msg'])
    try:

        cmdEnv = cfgCtx.env.env or None
        output = cfgCtx.cmd_and_log(cmd, env = cmdEnv)

        if parseFlags:
            cfgCtx.parse_flags(output, kwargs['uselib'], cfgCtx.env, kwargs['static'])

    except waferror.WafError as ex:
        cfgCtx.endMsg(kwargs['errmsg'], color = 'YELLOW')
        if log.verbose() > 1:
            cfgCtx.to_log('Command failure: %s' % ex)
        cfgCtx.fatal('The configuration failed')
    else:
        okmsg = kwargs.get('okmsg')
        if okmsg is not None:
            cfgCtx.endMsg(kwargs['okmsg'])

    return output

def _doPkgConfigForOne(cfgCtx, pkgInfo, actionArgs, taskParams):

    pkgname = pkgInfo.name

    defnames = actionArgs['defnames']
    if defnames is not None:
        defnames = {} if defnames is True else defnames
        defnames = defnames.get(pkgname, {})

    def setDefine(kind, value):
        if defnames is None:
            return

        defvar = defnames.get(kind, True)
        if defvar is True:
            if kind == 'have':
                defvar = cfgCtx.have_define(pkgname)
            else:
                assert kind == 'version'
                defvar = '%s_VERSION' % utils.normalizeForDefine(pkgname)

        if defvar:
            cfgCtx.define(defvar, value, quote = (kind == 'version') )
            # Is this really necessary ? Waf does it by default.
            #if kind == 'have':
            #    cfgCtx.env[defvar] = value

    getPkgVer = actionArgs.get('pkg-version', False)
    if getPkgVer:
        kwargs = actionArgs.copy()
        kwargs['msg'] = 'Getting version for %r' % pkgname
        kwargs['cmd-args'] = ['--modversion', pkgname]
        kwargs.pop('okmsg', None)
        version = _runToolConfig(cfgCtx, **kwargs)
        if version is not None:
            version = version.strip()
            # set *_VERSION define
            setDefine('version', version)
            cfgCtx.endMsg(version)

        if not actionArgs['libs'] and not actionArgs['cflags']:
            setDefine('have', 1)
            return

    # cmd line args
    cmdArgs = ['--%s' % x for x in ('libs', 'cflags', 'static') if actionArgs[x]]

    for k, v in viewitems(actionArgs.get('def-pkg-vars', {})):
        cmdArgs.append('--define-variable=%s=%s' % (k, v))

    cmdArgs += pkgInfo.cmdline
    actionArgs['cmd-args'] = cmdArgs

    actionArgs['uselib'] = pkgInfo.uselib
    actionArgs['parse-flags'] = True

    pkgline = "%r" % pkgname
    if pkgInfo.cmdline[0] != pkgname:
        nameLen = len(pkgname)
        verline = ' and '.join(x[nameLen + 1: ] for x in pkgInfo.cmdline)
        pkgline += ' (%s)' % verline

    actionArgs['msg'] = 'Checking for %s' % pkgline

    # run
    output = _runToolConfig(cfgCtx, **actionArgs)
    if output is None: # when mandatory == False
        return

    # set HAVE_* define
    setDefine('have', 1)

    # add to task
    taskUselib = taskParams.setdefault('uselib', [])
    taskUselib.append(pkgInfo.uselib)

def doPkgConfig(actionArgs, params):
    """
    Do pkg-config
    """

    cfgCtx     = params['cfgCtx']
    bconf      = params['bconf']
    taskParams = params['taskParams']

    toolname = actionArgs.setdefault('toolname', 'pkg-config')
    toolpaths = actionArgs.get('toolpaths', [])

    packages = actionArgs.get('packages')
    if not packages:
        msg = "The parameter 'packages' is empty in config action 'pkgconfig'"
        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    mandatory = actionArgs.get('mandatory', True)

    # find tool path
    kwargs = { 'mandatory' : mandatory, 'paths' : toolpaths}
    actionArgs['runpath'] = _findProgram(cfgCtx, toolname, **kwargs)

    cfgCtx.setenv(taskParams['$task.variant'])

    actionArgs.setdefault('libs', True)
    actionArgs.setdefault('cflags', True)
    actionArgs.setdefault('static', False)

    actionArgs['okmsg'] = 'yes'
    actionArgs['errmsg'] = 'not found'

    if 'tool-atleast-version' in actionArgs:
        ver = actionArgs['tool-atleast-version']
        actionArgs['msg'] = 'Checking for %s version >= %r' % (toolname, ver)
        actionArgs['cmd-args'] = ['--atleast-pkgconfig-version=%s' % ver]
        _runToolConfig(cfgCtx, **actionArgs)

    defnames = actionArgs.setdefault('defnames', True)
    if defnames is False:
        actionArgs['defnames'] = None

    pkgItems = _parsePkgConfigPackages(packages, bconf.path)
    for pkgInfo in pkgItems:
        _doPkgConfigForOne(cfgCtx, pkgInfo, actionArgs, taskParams)

def doToolConfig(actionArgs, params):
    """
    Do *-config like sdl-config, sdl2-config, mpicc, etc.
    """

    cfgCtx     = params['cfgCtx']
    bconf      = params['bconf']
    taskParams = params['taskParams']

    toolname = actionArgs.get('toolname')
    toolpaths = actionArgs.get('toolpaths', [])

    if not toolname:
        msg = "The parameter 'toolname' is empty in config action 'toolconfig'"
        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    actionArgs['cmd-args'] = utils.toList(actionArgs.pop('args', '--cflags --libs'))

    mandatory = actionArgs.get('mandatory', True)

    # find tool path
    kwargs = { 'mandatory' : mandatory, 'paths' : toolpaths}
    actionArgs['runpath'] = _findProgram(cfgCtx, toolname, **kwargs)

    uselib = toolname
    if toolname.endswith('-config'):
        uselib = toolname[:len(toolname)-len('-config')]
    uselib = utils.normalizeForDefine(uselib)

    actionArgs['uselib'] = uselib

    parseAs = actionArgs.pop('parse-as', 'flags-libs')
    actionArgs['parse-flags'] = (parseAs == 'flags-libs')
    actionArgs.setdefault('static', False)

    actionArgs.setdefault('msg', 'Checking for %s' % uselib)
    actionArgs['okmsg'] = 'yes'
    actionArgs['errmsg'] = 'not found'

    # run
    cfgCtx.setenv(taskParams['$task.variant'])
    output = _runToolConfig(cfgCtx, **actionArgs)
    if output is None: # when mandatory == False
        return

    defvar = actionArgs.get('defname')
    if not defvar and parseAs == 'flags-libs':
        defvar = 'HAVE_%s' % uselib

    if defvar:
        defval = 1
        quoteDefVal = False
        if parseAs == 'entire':
            defval = output.strip()
            quoteDefVal = True

        cfgCtx.define(defvar, defval, quote = quoteDefVal )

    if parseAs == 'flags-libs':
        # add to task
        taskUselib = taskParams.setdefault('uselib', [])
        taskUselib.append(uselib)

def writeConfigHeader(checkArgs, params):
    """ Write config header """

    buildtype  = params['buildtype']
    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']
    taskParams = params['taskParams']

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

    # remove the defines after they are added
    checkArgs['remove'] = checkArgs.pop('remove-defines', True)

    # write the configuration header from the build directory
    checkArgs['top'] = True

    cfgCtx.setenv(taskParams['$task.variant'])
    cfgCtx.write_config_header(fileName, **checkArgs)

def runActionsInParallel(actionArgs, params):
    """
    Run actions in parallel
    """

    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']
    taskParams = params['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    subactions = actionArgs.pop('actions', [])
    if not subactions:
        msg = "No actions for 'parallel' in config-actions for task %r" % taskName
        log.warn(msg)
        return

    supportedActions = (
        'call-pyfunc', 'check-headers', 'check-libs', 'check-code',
    )

    parallelActionArgsList = []
    params['parallel-actions'] = parallelActionArgsList

    for action in subactions:
        errMsg = None
        if isinstance(action, maptype):
            actionName = action.get('do')
            if not actionName:
                errMsg = "Parameter 'do' not found in parallel action '%r'" % action
            elif actionName not in supportedActions:
                errMsg = "action %r can not be used inside the 'parallel'" % actionName
                errMsg += ", task: %r!" % taskName
        elif callable(action):
            pass
        else:
            errMsg = "Action '%r' is not supported." % action

        if errMsg:
            cfgCtx.fatal(errMsg)

    _handleActions(subactions, params)
    params.pop('parallel-actions', None)

    if not parallelActionArgsList:
        return

    for args in parallelActionArgsList:
        args['msg'] = "  %s" % args['msg']

    _runActionsInParallelImpl(params, parallelActionArgsList, **actionArgs)

_cmnActionsFuncs = {
    'call-pyfunc'    : callPyFunc,
    'check-programs' : checkPrograms,
    'parallel'       : runActionsInParallel,
}

_actionsTable = { x:_cmnActionsFuncs.copy() for x in ToolchainVars.allLangs() }

def _handleActions(actions, params):

    for actionArgs in actions:
        if callable(actionArgs):
            actionArgs = {
                'do' : 'call-pyfunc',
                'func' : actionArgs,
            }
        else:
            # actionArgs is changed in conf action func below
            actionArgs = actionArgs.copy()

        ctx = params['cfgCtx']
        taskName = params['taskName']

        action = actionArgs.pop('do', None)
        if action is None:
            msg = "No 'do' in the configuration action %r for task %r!" \
                    % (actionArgs, taskName)
            ctx.fatal(msg)

        targetLang = params['taskParams'].get('$tlang')
        table = _actionsTable.get(targetLang, _cmnActionsFuncs)
        func = table.get(action)
        if not func:
            msg = "Unsupported action %r in the configuration actions for task %r!" \
                    % (action, taskName)
            ctx.fatal(msg)

        func(actionArgs, params)

def regActionFuncs(lang, funcs):
    """
    Register functions for configuration actions
    """

    _actionsTable[lang].update(funcs)

def runActions(actions, params):
    """
    Run configuration actions
    """

    _handleActions(actions, params)
