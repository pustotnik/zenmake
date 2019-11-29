# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from collections import defaultdict

# NOTICE:This module must import modules with original Waf context classes
# before declaring their alter implementions.
# Otherwise classes in this module can be ignored. In normal case of
# using of the Waf such classes are created in the 'wscript' because this
# file is loaded always after all Waf context classes.

from waflib.Context import Context as WafContext
from waflib.Configure import ConfigurationContext as WafConfContext
from waflib import Errors as waferror
from zm.autodict import AutoDict as _AutoDict
from zm.pyutils import viewitems
from zm import utils, log, toolchains
from zm.waf import assist

joinpath = os.path.join

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
        cfgCtx.end_msg(result = 'failed', color = 'YELLOW')
        if mandatory:
            cfgCtx.fatal('Checking by function %r failed' % func.__name__)
    else:
        cfgCtx.end_msg('ok')

def _confTestCheckPrograms(entity, **kwargs):
    cfgCtx = kwargs['cfgCtx']

    cfgCtx.setenv('')
    called = kwargs['called'][id(cfgCtx.env)]

    names = utils.toList(entity.pop('names', []))
    funcArgs = entity
    funcArgs['path_list'] = utils.toList(entity.pop('paths', []))

    for name in names:
        # It doesn't matter here that 'hash' can produce different result
        # between python runnings.
        _hash = hash( ('find_program', name, repr(sorted(funcArgs.items())) ) )
        if _hash not in called:
            cfgCtx.find_program(name, **funcArgs)
            called.add(_hash)

def _confTestCheck(entity, **kwargs):
    cfgCtx = kwargs['cfgCtx']
    taskParams = kwargs['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])
    called = kwargs['called'][id(cfgCtx.env)]
    funcArgs = entity
    _hash = hash( ('check', repr(sorted(funcArgs.items())) ) )
    if _hash not in called:
        cfgCtx.check(**funcArgs)
        called.add(_hash)

def _confTestCheckSysLibs(entity, **kwargs):
    taskParams = kwargs['taskParams']

    sysLibs = utils.toList(taskParams.get('sys-libs', []))
    funcArgs = entity
    for lib in sysLibs:
        funcArgs['lib'] = lib
        _confTestCheck(funcArgs, **kwargs)

def _confTestCheckHeaders(entity, **kwargs):
    headers = utils.toList(entity.pop('names', []))
    funcArgs = entity
    for header in headers:
        funcArgs['header_name'] = header
        _confTestCheck(funcArgs, **kwargs)

def _confTestCheckLibs(entity, **kwargs):
    libs = utils.toList(entity.pop('names', []))
    autodefine = entity.pop('autodefine', False)
    funcArgs = entity
    for lib in libs:
        funcArgs['lib'] = lib
        if autodefine:
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

    cfgCtx.write_config_header(fileName, **entity)

_confTestFuncs = {
    'check-by-pyfunc'     : _confTestCheckByPyFunc,
    'check-programs'      : _confTestCheckPrograms,
    'check-sys-libs'      : _confTestCheckSysLibs,
    'check-headers'       : _confTestCheckHeaders,
    'check-libs'          : _confTestCheckLibs,
    'check'               : _confTestCheck,
    'write-config-header' : _confTestWriteHeader,
}

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable=no-member,attribute-defined-outside-init

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

        called = defaultdict(set)

        for taskName, taskParams in viewitems(tasks):
            confTests = taskParams.get('conftests', [])
            funcKWArgs = dict(
                cfgCtx = self,
                buildtype = buildtype,
                taskName = taskName,
                taskParams = taskParams,
                called = called,
            )
            for entity in confTests:
                if callable(entity):
                    entity = {
                        'act' : 'check-by-pyfunc',
                        'func' : entity,
                    }
                else:
                    entity = entity.copy()
                act = entity.pop('act', None)
                func = _confTestFuncs.get(act, None)
                if not func:
                    self.fatal('unknown act %r for conftests in task %r!' %
                               (act, taskName))

                func(entity, **funcKWArgs)

        self.setenv('')

    def configureTaskParams(self, bconf, taskName, taskParams):
        """
        Handle every known task param that can be handled at configure stage.
        It is better for common performance because command 'configure' is used
        rarely then 'build'.
        """

        btypeDir = bconf.selectedBuildTypeDir
        rootdir  = bconf.rootdir
        startdir = bconf.startdir
        taskParams['name'] = taskName

        features = assist.detectConfTaskFeatures(taskParams)

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
