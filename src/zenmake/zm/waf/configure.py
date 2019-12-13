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

from waflib import ConfigSet
from waflib.Context import Context as WafContext, create_context as createContext
from waflib.Configure import ConfigurationContext as WafConfContext
from waflib.Configure import conf
from waflib import Errors as waferror
from zm.constants import CONFTEST_DIR_PREFIX
from zm.autodict import AutoDict as _AutoDict
from zm.pyutils import maptype, viewitems, viewvalues
from zm import utils, log, toolchains
from zm.waf import assist

joinpath = os.path.join

CONF_CHECK_CACHE_FILE = 'conf_check_cache'
CONF_CHECK_CACHE_KEY = 'conf-check-cache'

def _confTestCheckByPyFunc(entity, **kwargs):
    cfgCtx    = kwargs['cfgCtx']
    buildtype = kwargs['buildtype']
    taskName  = kwargs['taskName']

    func = entity['func']
    funcArgCount = func.__code__.co_argcount
    mandatory = entity.pop('mandatory', True)

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

def _confTestCheckPrograms(entity, **kwargs):
    cfgCtx = kwargs['cfgCtx']

    cfgCtx.setenv('')

    names = utils.toList(entity.pop('names', []))
    funcArgs = entity
    funcArgs['path_list'] = utils.toList(entity.pop('paths', []))

    for name in names:
        # Method find_program caches result in the cfgCtx.env and
        # therefore it's not needed to cache it here.
        cfgCtx.find_program(name, **funcArgs)

def _confTestCheckSysLibs(entity, **kwargs):
    taskParams = kwargs['taskParams']

    sysLibs = utils.toList(taskParams.get('sys-libs', []))
    funcArgs = entity
    funcArgs['names'] = sysLibs
    _confTestCheckLibs(funcArgs, **kwargs)

def _confTestCheckHeaders(entity, **kwargs):
    headers = utils.toList(entity.pop('names', []))
    funcArgs = entity
    for header in headers:
        funcArgs['msg'] = 'Checking for header %s' % header
        funcArgs['header_name'] = header
        _confTestCheck(funcArgs, **kwargs)

def _confTestCheckLibs(entity, **kwargs):
    libs = utils.toList(entity.pop('names', []))
    autodefine = entity.pop('autodefine', False)
    for lib in libs:
        funcArgs = entity.copy()
        funcArgs['msg'] = 'Checking for library %s' % lib
        funcArgs['lib'] = lib
        if autodefine and 'define_name' not in funcArgs:
            funcArgs['define_name'] = 'HAVE_LIB_' + lib.upper()
        _confTestCheck(funcArgs, **kwargs)

def _confTestWriteHeader(entity, **kwargs):

    buildtype  = kwargs['buildtype']
    cfgCtx     = kwargs['cfgCtx']
    taskName   = kwargs['taskName']
    taskParams = kwargs['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    def defaultFileName():
        return utils.normalizeForFileName(taskName).lower()

    fileName = entity.pop('file', '%s_%s' %
                          (defaultFileName(), 'config.h'))
    fileName = joinpath(buildtype, fileName)
    projectName = cfgCtx.getbconf().projectName or ''
    guardname = utils.normalizeForDefine(projectName + '_' + fileName)
    entity['guard'] = entity.pop('guard', guardname)
    # write the configuration header from the build directory
    entity['top'] = True

    cfgCtx.write_config_header(fileName, **entity)

def _confTestCheck(entity, **kwargs):
    cfgCtx = kwargs['cfgCtx']
    taskParams = kwargs['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    # _confTestCheck is used in loops so it's needed to save entity
    # without changes
    funcArgs = entity.copy()

    #TODO: add as option
    # if it is False then write-config-header doesn't write defines
    #funcArgs['global_define'] = False

    parallelChecks = funcArgs.pop('parallel-checks', None)

    if parallelChecks is not None:
        # funcArgs is shared so it can be changed later
        parallelChecks.append(funcArgs)
    else:
        cfgCtx.check(**funcArgs)

def _confTestCheckInParallel(entity, **kwargs):
    cfgCtx     = kwargs['cfgCtx']
    taskName   = kwargs['taskName']
    taskParams = kwargs['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    checks = entity.pop('checks', [])
    if not checks:
        msg = "No checks for act 'parallel' in conftests for task %r" % taskName
        log.warn(msg)
        return

    supportedActs = (
        'check-sys-libs', 'check-headers',
        'check-libs', 'check',
    )

    parallelCheckArgsList = []

    for check in checks:
        check['parallel-checks'] = parallelCheckArgsList
        if check['act'] not in supportedActs:
            msg = "act %r can not be used inside the act 'parallel'" % check['act']
            msg += " for conftests in task %r!" % taskName
            cfgCtx.fatal(msg)

    _runConfChecks(checks, kwargs)
    if not parallelCheckArgsList:
        return

    # It's necessary to remove any locks after previous serial checks
    # because they are fake locks. See run_build in this file.
    cfgCtx.confChecks['check-locks'].clear()

    for args in parallelCheckArgsList:
        args['msg'] = "  %s" % args['msg']

    params = dict(
        msg = 'Checking in parallel',
    )
    cfgCtx.multicheck(*parallelCheckArgsList, **params)

    # It's better to remove all locks after last parallel checks.
    cfgCtx.confChecks['check-locks'].clear()

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

def _runConfChecks(checks, funcArgs):
    for entity in checks:
        if callable(entity):
            entity = {
                'act' : 'check-by-pyfunc',
                'func' : entity,
            }
        else:
            # entity is changed in conf test func below
            entity = entity.copy()
        act = entity.pop('act', None)
        func = _confTestFuncs.get(act, None)
        if not func:
            ctx = funcArgs['cfgCtx']
            taskName = funcArgs['taskName']
            ctx.fatal('unknown act %r for conftests in task %r!' %
                      (act, taskName))

        func(entity, **funcArgs)

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable=no-member,attribute-defined-outside-init

    def __init__(self, *args, **kwargs):
        super(ConfigurationContext, self).__init__(*args, **kwargs)

        self.confChecks = {}
        self.confChecks['cache'] = None
        self.confChecks['top-lock'] = utils.threading.Lock()
        self.confChecks['check-locks'] = {}

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
            funcArgs = dict(
                cfgCtx = self,
                buildtype = buildtype,
                taskName = taskName,
                taskParams = taskParams,
            )
            _runConfChecks(confTests, funcArgs)

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
def calcConfCheckHash(self, checkArgs):
    """
    Get hash for conf check
    """

    buf = []
    for key in sorted(checkArgs.keys()):
        if key == 'multicheck_mandatory':
            continue
        v = checkArgs[key]
        if hasattr(v, '__call__'):
            buf.append(utils.hashOfFunc(v))
        else:
            buf.append(str(v))
    # to ensure it's an unique id for current conf check
    buf.append(self.variant)

    kwhash = utils.hashOfStrs(buf)
    return utils.hexOfStr(kwhash)

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
    dirpath += '%s%d' % (CONFTEST_DIR_PREFIX, checkId)
    return dirpath

def _makeConfTestBld(ctx, checkArgs, topdir, bdir):
    clsName = checkArgs.get('run_build_cls') or getattr(ctx, 'run_build_cls', 'build')
    bld = createContext(clsName, top_dir = topdir, out_dir = bdir)

    # avoid unnecessary directory
    bld.variant = ''

    bld.init_dirs()
    bld.progress_bar = 0
    bld.targets = '*'

    bld.logger = ctx.logger
    bld.all_envs.update(ctx.all_envs)
    bld.env = checkArgs['env']

    bld.kw = checkArgs # for function 'build_fun'
    bld.conf = ctx
    return bld

class _RunBuildLock(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        if self.lock:
            return self.lock.__enter__()
        return None

    def __exit__(self, _type, value, traceback):
        if self.lock:
            self.lock.__exit__(_type, value, traceback)

@conf
def run_build(self, *k, **kw):
    """
    Create a temporary build context to execute a build.
    It's alternative version of the waflib.Configure.run_build
    """

    # pylint: disable = invalid-name,unused-argument

    try:
        topCtx = self.multicheck_task.conf
    except AttributeError:
        topCtx = self
        ctxLock = checkLock = _RunBuildLock(None)
    else:
        # It's called from cfgtask by conf.multicheck
        # So it's needed to be locked
        checkLock = None
        ctxLock = _RunBuildLock(topCtx.confChecks['top-lock'])
        def makeCheckLock():
            return _RunBuildLock(utils.threading.Lock())

    checkHash = topCtx.calcConfCheckHash(kw)

    with ctxLock: # global lock for topCtx
        if checkLock is None:
            checkLocks = topCtx.confChecks['check-locks']
            checkLock = checkLocks.setdefault(checkHash, makeCheckLock())
        # it should be called with ctx lock
        checkCache = topCtx.getConfCheckCache(checkHash)

    with checkLock: # lock for current conf test only

        # it should be called with checkLock otherwise cache will not work
        if 'retval' in checkCache:
            return checkCache['retval']

        checkId = checkCache['id']

        topdir = _calcConfCheckDir(topCtx, checkId)
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

        self.test_bld = bld = _makeConfTestBld(self, kw, topdir, bdir)

        kw['build_fun'](bld)
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
            with ctxLock:
                checkCache['retval'] = ret

    return ret
