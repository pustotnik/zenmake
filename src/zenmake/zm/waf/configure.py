# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import shlex

# NOTICE:This module must import modules with original Waf context classes
# before declaring their alter implementions.
# Otherwise classes in this module can be ignored. In normal case of
# using of the Waf such classes are created in the 'wscript' because this
# file is loaded always after all Waf context classes.

from waflib import Errors as waferror
from waflib.ConfigSet import ConfigSet
from waflib.Context import Context as WafContext
from waflib.Configure import ConfigurationContext as WafConfContext
from zm.autodict import AutoDict as _AutoDict
from zm.pyutils import viewitems, viewvalues
from zm import utils, log, toolchains, error
from zm.features import TASK_TARGET_FEATURES_TO_LANG, TASK_LANG_FEATURES
from zm.features import ToolchainVars
from zm.waf import assist
from zm.conftests import handleConfTests

#pylint: disable=unused-import
# This modules must be just imported
from zm.waf import options, context
#pylint: enable=unused-import

joinpath = os.path.join

CONF_CACHE_FILE = 'conf.cache'

def _genToolAutoName(lang):
    return 'auto-%s' % lang.replace('xx', '++')

TOOL_AUTO_NAMES = { _genToolAutoName(x) for x in ToolchainVars.allLangs() }

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable=no-member,attribute-defined-outside-init

    def __init__(self, *args, **kwargs):
        super(ConfigurationContext, self).__init__(*args, **kwargs)

        self._loadedTools = {}
        self._toolchainEnvs = {}
        self._confCache = None
        self.monitFiles = []

        self.validToolchainNames = assist.getValidPreDefinedToolchainNames()

    def _calcObjectsIndex(self, bconf, taskParams):

        # In this way indexes for object files aren't changed from build to build
        # while in Waf way they can be changed.

        cache = self.getConfCache()
        if 'object-idx' not in cache:
            cache['object-idx'] = {}

        indexes = cache['object-idx']
        key = '%s%s%s' % (bconf.path, os.pathsep, taskParams['name'])
        lastIdx = indexes.get('last-idx', 0)

        idx = taskParams.get('objfile-index')
        if idx is not None:
            if idx > lastIdx:
                indexes['last-idx'] = idx
            indexes[key] = idx
        else:
            idx = indexes.get(key)
            if idx is None:
                indexes['last-idx'] = idx = lastIdx + 1
                indexes[key] = idx
        return idx

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

    def _loadConfCache(self):

        # self.env can not be used for a cache because it is not loaded
        # on 'configure' and always is empty at the begining

        cachePath = joinpath(self.cachedir.abspath(), CONF_CACHE_FILE)
        try:
            cache = ConfigSet(cachePath)
        except EnvironmentError:
            cache = ConfigSet()

        return cache

    def getConfCache(self):
        """
        Get conf cache
        """

        if self._confCache is None:
            self._confCache = self._loadConfCache()

        return self._confCache

    # override
    def execute(self):

        # See details here: https://gitlab.com/ita1024/waf/issues/1563
        self.env.NO_LOCK_IN_RUN = True
        self.env.NO_LOCK_IN_TOP = True

        super(ConfigurationContext, self).execute()

        self.monitFiles.extend([x.path for x in self.bconfManager.configs])
        filePath = self.bconfManager.root.confPaths.zmcmnconfset
        assist.dumpZenMakeCmnConfSet(self.monitFiles, filePath)

        if self._confCache is not None:
            cachePath = joinpath(self.cachedir.abspath(), CONF_CACHE_FILE)
            self._confCache.store(cachePath)

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

            features = utils.toListSimple(taskParams.get('features', []))
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

    def loadToolchains(self, bconf):
        """
        Load all selected toolchains
        """

        toolchainNames = self.handleToolchains(bconf)
        self._checkToolchainNames(bconf)

        toolchainsEnvs = self._toolchainEnvs
        oldEnvName = self.variant
        customToolchains = bconf.customToolchains
        detectedToolNames = {}
        emptyEnv = ConfigSet()

        def loadToolchain(toolchain):

            if toolchain in toolchainsEnvs:
                #don't load again
                return

            self.setenv(toolchain, env = emptyEnv)

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

    def getToolchainEnvs(self):
        """
        Get envs for all loaded toolchains
        """

        return self._toolchainEnvs

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
            handleConfTests(confTests, params)

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
        assist.handleTaskLibPathParams(taskParams, rootdir, startdir)
        assist.handleTaskExportDefinesParam(taskParams)

        taskParams['target'] = targetPath

        #counter for the object file extension
        taskParams['objfile-index'] = self._calcObjectsIndex(bconf, taskParams)

        prjver = bconf.projectVersion
        if prjver and 'ver-num' not in taskParams:
            taskParams['ver-num'] = prjver

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
