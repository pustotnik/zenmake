# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import shutil

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
from zm.pyutils import maptype, viewitems, viewvalues
from zm import utils, log, toolchains
from zm.waf import assist

joinpath = os.path.join

CONF_CHECK_CACHE_FILE = 'conf_check_cache'
CONFTEST_HASH_USE_ENV_KEYS = set(
    ('DEST_BINFMT', 'DEST_CPU', 'DEST_OS')
)
for _var in toolchains.CompilersInfo.allVarsToSetCompiler():
    CONFTEST_HASH_USE_ENV_KEYS.add(_var)
    CONFTEST_HASH_USE_ENV_KEYS.add('%s_VERSION' % _var)
    CONFTEST_HASH_USE_ENV_KEYS.add('%s_NAME' % _var)

class CfgCheckTask(Task.Task):
    """
    A task that executes build configuration tests (calls conf.check).
    It's used to run conf checks in parallel.
    """

    def __init__(self, *args, **kwargs):
        Task.Task.__init__(self, *args, **kwargs)

        self.args = None
        self.conf = None
        self.bld = None
        self.logger = None

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
        args = self.args
        try:
            mandatory = args.get('mandatory', True)
            args['mandatory'] = True
            try:
                bld.check(**args)
            finally:
                args['mandatory'] = mandatory
        except Exception:
            return 1
        return 0

    def process(self):

        Task.Task.process(self)
        if 'msg' not in self.args:
            return
        with self.generator.bld.cmnLock:
            self.conf.start_msg(self.args['msg'])
            if self.hasrun == Task.NOT_RUN:
                self.conf.end_msg('test cancelled', 'YELLOW')
            elif self.hasrun != Task.SUCCESS:
                self.conf.end_msg(self.args.get('errmsg', 'no'), 'YELLOW')
            else:
                self.conf.end_msg(self.args.get('okmsg', 'yes'), 'GREEN')

class _RunnerBldCtx(object):
    """
    A class that is used as BuildContext to execute conf tests in parallel
    """

    # pylint: disable = invalid-name, missing-docstring

    def __init__(self, tasks):
        self.keep = False
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
    bld = _RunnerBldCtx(tasks)

    bld.keep = kwargs.get('tryall', True)

    idToTask = {}
    for i, args in enumerate(checkArgsList):
        args['$parallel-id'] = i
        checkTask = CfgCheckTask(env = None)
        tasks.append(checkTask)
        checkTask.args = args
        checkTask.conf = self
        checkTask.bld = bld # to use in task.log_display(task.generator.bld)

        # bind a logger that will keep the info in memory
        checkTask.logger = log.makeMemLogger(str(id(checkTask)), self.logger)

        if 'id' in args:
            idToTask[args['id']] = checkTask

    def applyDeps(idToTask, task, before):
        tasks = task.args.get('before' if before else 'after', [])
        for key in utils.toList(tasks):
            otherTask = idToTask.get(key, None)
            if not otherTask:
                raise ValueError('No test named %r' % key)
            if before:
                otherTask.run_after.add(task)
            else:
                task.run_after.add(otherTask)

    # second pass to set dependencies with after_test/before_test
    for tsk in tasks:
        applyDeps(idToTask, tsk, before = True)
        applyDeps(idToTask, tsk, before = False)

    def getTasksGenerator():
        yield tasks
        while 1:
            yield []

    bld.producer = scheduler = Runner.Parallel(bld, Options.options.jobs)
    scheduler.biter = getTasksGenerator()

    self.end_msg('started')
    scheduler.start()

    # flush the logs in order into the config.log
    for tsk in tasks:
        tsk.logger.memhandler.flush()

    self.start_msg('-> processing test results')

    for err in scheduler.error:
        if not getattr(err, 'err_msg', None):
            continue
        self.to_log(err.err_msg)
        self.end_msg('fail', color = 'RED')
        msg = 'There is an error in the library, read config.log for more information'
        raise waferror.WafError(msg)

    failureCount = len([x for x in tasks if x.hasrun not in (Task.SUCCESS, Task.NOT_RUN)])

    if failureCount:
        self.end_msg('%s test(s) failed' % failureCount, color = 'YELLOW')
    else:
        self.end_msg('all ok')

    for tsk in tasks:
        if tsk.hasrun != Task.SUCCESS and tsk.args.get('mandatory', True):
            self.fatal('One of the tests has failed, read config.log for more information')

        # in rare case we get "No handlers could be found for logger"
        log.freeLogger(tsk.logger)

@conf
def loadConfCheckCache(self):
    """
    Load cache data for conf checks.
    """

    cachePath = joinpath(self.cachedir.abspath(), CONF_CHECK_CACHE_FILE)
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

@conf
def getConfCheckCache(self, checkHash):
    """
    Get conf check cache by hash
    """

    cache = self.confChecks['cache']
    if cache is None:
        self.confChecks['cache'] = cache = self.loadConfCheckCache()

    checks = cache['checks']
    if checkHash not in checks:
        lastId = checks.get('last-id', 0)
        checks['last-id'] = currentId = lastId + 1
        checks[checkHash] = {}
        checks[checkHash]['id'] = currentId

    return checks[checkHash]

def _calcConfCheckDir(ctx, checkId):

    dirpath = ctx.bldnode.abspath() + os.sep
    dirpath += '%s%s' % (CONFTEST_DIR_PREFIX, checkId)
    return dirpath

def _makeConfTestBld(ctx, checkArgs, topdir, bdir):

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

    if isinstance(self, WafConfContext):
        cfgCtx = self
    else:
        # self is a BuildContext
        cfgCtx = self.cfgCtx

    # this function can not be called from conf.multicheck
    assert not hasattr(self, 'multicheck_task')

    checkHash = checkArgs['$conf-test-hash']
    checkCache = cfgCtx.confChecks['cache']['checks'][checkHash]

    retval = checkCache['retval']
    if retval is not None:
        return retval

    checkId = str(checkCache['id'])
    if '$parallel-id' in checkArgs:
        checkId = '%s.%s' % (checkId, checkArgs['$parallel-id'])

    topdir = _calcConfCheckDir(cfgCtx, checkId)
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

    self.test_bld = bld = _makeConfTestBld(self, checkArgs, topdir, bdir)

    checkArgs['build_fun'](bld)
    ret = -1

    try:
        try:
            bld.compile()
        except waferror.WafError:
            import traceback
            ret = 'Conf test failed: %s' % traceback.format_exc()
            self.fatal(ret)
        else:
            ret = getattr(bld, 'retval', 0)
    finally:
        shutil.rmtree(topdir)
        checkCache['retval'] = ret

    return ret

def _calcConfCheckHexHash(checkArgs, params):

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    hashVals = {}
    for k, v in viewitems(checkArgs):
        if k in ('mandatory', ):
            continue
        hashVals[k] = v
    # just in case
    hashVals['toolchain'] = taskParams.get('toolchain', '')

    buff = [ '%s: %s' % (k, str(hashVals[k])) for k in sorted(hashVals.keys()) ]

    env = cfgCtx.env
    envStr = ''
    for k in sorted(env.keys()):
        if k not in CONFTEST_HASH_USE_ENV_KEYS:
            # these keys are not significant for hash but can make cache misses
            continue
        val = env[k]
        envStr += '%r %r ' % (k, val)
    buff.append('%s: %s' % ('env', envStr))

    return utils.hexOfStr(utils.hashOfStrs(buff))

def _confTestCheckByPyFunc(checkArgs, params):
    cfgCtx    = params['cfgCtx']
    buildtype = params['buildtype']
    taskName  = params['taskName']

    func = checkArgs['func']
    funcArgCount = func.__code__.co_argcount
    mandatory = checkArgs.pop('mandatory', True)

    cfgCtx.start_msg('Checking by function %r' % func.__name__)
    if funcArgCount == 0:
        result = func()
    else:
        result = func(task = taskName, buildtype = buildtype)

    if not result:
        cfgCtx.end_msg(result = 'no', color = 'YELLOW')
        if mandatory:
            cfgCtx.fatal('Checking by function %r failed' % func.__name__)
    else:
        cfgCtx.end_msg('yes')

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
    checkCache = cfgCtx.getConfCheckCache(hexHash)
    if 'retval' not in checkCache:
        # to use it without lock in threads we need to insert this key
        checkCache['retval'] = None
    checkArgs['$conf-test-hash'] = hexHash

    #TODO: add as option
    # if it is False then write-config-header doesn't write defines
    #checkArgs['global_define'] = False

    parallelChecks = params.get('parallel-checks', None)

    if parallelChecks is not None:
        # checkArgs is shared so it can be changed later
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
        'check-libs', 'check',
    )

    parallelCheckArgsList = []
    params['parallel-checks'] = parallelCheckArgsList

    for check in subchecks:
        if check['act'] not in supportedActs:
            msg = "act %r can not be used inside the act 'parallel'" % check['act']
            msg += " for conftests in task %r!" % taskName
            cfgCtx.fatal(msg)

    _runConfChecks(subchecks, params)
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
    'check'               : _confTestCheck,
    'parallel'            : _confTestCheckInParallel,
    'write-config-header' : _confTestWriteHeader,
}

def _runConfChecks(checks, params):
    for checkArgs in checks:
        if callable(checkArgs):
            checkArgs = {
                'act' : 'check-by-pyfunc',
                'func' : checkArgs,
            }
        else:
            # checkArgs is changed in conf test func below
            checkArgs = checkArgs.copy()

        act = checkArgs.pop('act', None)
        func = _confTestFuncs.get(act, None)
        if not func:
            ctx = params['cfgCtx']
            taskName = params['taskName']
            ctx.fatal('unknown act %r for conftests in task %r!' %
                      (act, taskName))

        func(checkArgs, params)

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable=no-member,attribute-defined-outside-init

    def __init__(self, *args, **kwargs):
        super(ConfigurationContext, self).__init__(*args, **kwargs)

        self.confChecks = {}
        self.confChecks['cache'] = None

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

        assist.dumpZenMakeCmnConfSet(self.bconfManager)

        cache = self.confChecks['cache']
        if cache is not None:
            cachePath = joinpath(self.cachedir.abspath(), CONF_CHECK_CACHE_FILE)
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
            _runConfChecks(confTests, params)

        self.setenv('')

    def configureTaskParams(self, bconf, taskParams):
        """
        Handle every known task param that can be handled at configure stage.
        It is better for common performance because command 'configure' is used
        rarely then 'build'.
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
        assist.handleTaskExportDefinesParam(taskParams)
        assist.handleTaskCommonPathParam(taskParams, 'sys-lib-path', rootdir, startdir)

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
            ('sys-lib-path', 'libpath', None),
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
