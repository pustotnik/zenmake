# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import shlex
import time
import platform

# NOTICE:This module must import modules with original Waf context classes
# before declaring their alter implementions.
# Otherwise classes in this module can be ignored. In normal case of
# using of the Waf such classes are created in the 'wscript' because this
# file is loaded always after all Waf context classes.

from waflib import Errors as waferror, Context as WafContext
from waflib.ConfigSet import ConfigSet
from waflib.Configure import ConfigurationContext as WafConfContext
from zm.constants import ZENMAKE_CONF_CACHE_PREFIX, WAF_CACHE_DIRNAME, WAF_CONFIG_LOG
from zm.constants import TASK_TARGET_KINDS
from zm.pyutils import viewitems, viewvalues, viewkeys
from zm import utils, log, toolchains, error, db, version, cli
from zm.buildconf.select import handleOneTaskParamSelect, handleTaskParamSelects
from zm.deps import configureExternalDeps, produceExternalDeps
from zm.features import TASK_TARGET_FEATURES_TO_LANG, TASK_LANG_FEATURES
from zm.features import ToolchainVars
from zm.waf import assist, context
from zm.conftests import handleConfTests

joinpath = os.path.join
normpath = os.path.normpath

toList       = utils.toList
toListSimple = utils.toListSimple

def _genToolAutoName(lang):
    return 'auto-%s' % lang.replace('xx', '++')

TOOL_AUTO_NAMES = { _genToolAutoName(x) for x in ToolchainVars.allLangs() }

CONFLOG_HEADER_TEMPLATE = '''# Project %(prj)s configured on %(now)s by
# ZenMake %(zmver)s, based on Waf %(wafver)s (abi %(wafabi)s)
# python %(pyver)s on %(systype)s
# using %(args)s
#'''

class ConfigurationContext(WafConfContext):
    """ Context for command 'configure' """

    # pylint: disable = no-member,attribute-defined-outside-init
    # pylint: disable = too-many-instance-attributes

    def __init__(self, *args, **kwargs):
        super(ConfigurationContext, self).__init__(*args, **kwargs)

        self._loadedTools = {}
        self._toolchainEnvs = {}
        self._btasks = None
        self._confCache = None
        self.monitFiles = []
        self.zmMetaConfAttrs = {}

        self.validToolchainNames = assist.getValidPreDefinedToolchainNames()

    def _handleTaskExportDefinesParam(self, taskParams):
        """
        Get valid 'export-defines' for build task
        """

        exportDefines = taskParams.get('export-defines', None)
        if not exportDefines:
            taskParams.pop('export-defines', None)
            return

        if isinstance(exportDefines, bool) and exportDefines:
            exportDefines = taskParams.get('defines', [])

        taskParams['export-defines'] = toList(exportDefines)

    def _handleMonitLibs(self, taskParams):

        for libsparam in ('libs', 'stlibs'):
            monitparam = 'monit' + libsparam
            monitLibs = taskParams.get(monitparam, None)
            if monitLibs is None:
                continue

            libs = taskParams.get(libsparam, [])
            if isinstance(monitLibs, bool):
                monitLibs = set(libs) if monitLibs else None
            else:
                monitLibs = set(monitLibs)
                monitLibs.intersection_update(libs)

            if not monitLibs:
                taskParams.pop(monitparam, None)
            else:
                taskParams[monitparam] = sorted(monitLibs)

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

    def _mergeTasks(self):

        tasks = {}
        for bconf in self.bconfManager.configs:
            tasks.update(bconf.tasks)

        self._btasks = tasks

    def _postCheckTasks(self):

        allTasks = self._btasks
        for bconf in self.bconfManager.configs:
            for taskParams in viewvalues(bconf.tasks):
                for localDep in taskParams.get('use', []):
                    if localDep not in allTasks:
                        taskName = taskParams['name']
                        msg = 'Task %r: local dependency %r not found.' % (taskName, localDep)
                        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    def _loadTool(self, tool, **kwargs):

        tooldirs = kwargs.get('tooldirs', None)
        withSysPath = kwargs.get('withSysPath', True)
        toolId = kwargs.get('id', '')

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
                    raise error.ZenMakeConfError(msg, confpath = bconf.path)

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

    def loadCaches(self):
        """
        Load cache files needed for 'configure'
        """

        cachePath = joinpath(self.cachedir.abspath(), ZENMAKE_CONF_CACHE_PREFIX)
        try:
            cache = db.loadFrom(cachePath)
        except EnvironmentError:
            cache = {}

        # protect from format changes
        zmversion = cache.get('zmversion', '')
        if zmversion != version.current():
            cache = { 'zmversion' : version.current() }

        self._confCache = cache

    def saveCaches(self):
        """
        Save cache files needed for 'configure' and for 'build'
        """

        bconfManager = self.bconfManager
        rootbconf = bconfManager.root
        bconfPaths = rootbconf.confPaths
        cachedir = bconfPaths.zmcachedir

        # common conf cache
        if self._confCache is not None:
            cachePath = joinpath(cachedir, ZENMAKE_CONF_CACHE_PREFIX)
            db.saveTo(cachePath, self._confCache)

        # Waf always loads all *_cache.py files in directory 'c4che' during
        # build step. So it loads all stored variants even though they
        # aren't needed. And therefore it's better to save variants in
        # different files and load only needed ones.

        tasks = self._btasks

        envs = {}
        for taskParams in viewvalues(tasks):
            taskVariant = taskParams['$task.variant']

            # It's necessary to delete variant from conf.all_envs. Otherwise
            # Waf stores it in 'c4che'.
            env = self.all_envs.pop(taskVariant)
            envs[taskVariant] = utils.configSetToDict(env)

        buildtype = rootbconf.selectedBuildType

        tasksData = {
            'tasks'     : tasks,
            'taskenvs'  : envs,
            'buildtype' : buildtype,
            'depconfs'  : self.zmdepconfs,
        }

        cachePath = assist.makeTasksCachePath(cachedir, buildtype)
        db.saveTo(cachePath, tasksData)

        self.zmcache().tasksDb = tasksData

    def getConfCache(self):
        """
        Get conf cache
        """
        return self._confCache

    # override
    def post_recurse(self, node):
        # Avoid some actions from WafConfContext.post_recurse.
        # It's mostly for performance.
        WafContext.Context.post_recurse(self, node)

    # override
    def store(self):
        self.saveCaches()
        super(ConfigurationContext, self).store()

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
                msg = "%r is not valid name" % toolchain
                msg += " in the variable 'toolchains'"
                raise error.ZenMakeConfError(msg, confpath = bconf.path)

            settings = customToolchains[toolchain]

            # OS env vars
            settings.vars.update(sysEnvToolVars)
            settings.vars.update(sysEnvFlagVars)
            settings.kind = toolchain if not settings.kind else settings.kind

        toolchainNames = set()

        for taskParams in viewvalues(bconf.tasks):

            features = toListSimple(taskParams.get('features', []))
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
                _toolchains = toList(taskParams.get('toolchain', []))

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
                msg = "toolchains.%s" % toolchain
                msg += " must have field 'kind' with one of the values: "
                msg += str(allowedNames)[1:-1]
                raise error.ZenMakeConfError(msg, confpath = bconf.path)

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

    def addExtraMonitFiles(self, bconf):
        """
        Add extra file paths to monitor for autoconfig feature
        """

        files = bconf.features.get('monitor-files')
        if not files:
            return
        for path in files.abspaths():
            if not os.path.isfile(path):
                msg = "Error in the file %r:\n" % bconf.path
                msg += "File path %r " % path
                msg += "from the features.monitor-files doesn't exist"
                self.fatal(msg)
            self.monitFiles.append(path)

    def runConfTests(self, buildtype, tasks):
        """
        Run supported configuration tests/checks
        """

        try:
            printLogo = self._printLogo
        except AttributeError:
            self._printLogo = printLogo = True

        for taskName, taskParams in viewitems(tasks):
            confTests = taskParams.get('conftests', [])
            if not confTests:
                continue
            if printLogo:
                log.printStep('Running configuration tests')
                printLogo = False
            log.info('.. Checks for the %r:' % taskName)
            params = {
                'cfgCtx' : self,
                'buildtype' : buildtype,
                'taskName' : taskName,
                'taskParams' : taskParams,
            }
            handleConfTests(confTests, params)

        self._printLogo = printLogo
        self.setenv('')

    def configureTaskParams(self, bconf, taskParams):
        """
        Handle every known task param that can be handled at configure stage.
        It is better for common performance because command 'configure' is used
        rarely than command 'build'.
        """

        startdir = bconf.startdir

        assist.handleTaskIncludesParam(taskParams, startdir)
        assist.handleTaskLibPathParams(taskParams)
        self._handleTaskExportDefinesParam(taskParams)
        self._handleMonitLibs(taskParams)

        #counter for the object file extension
        taskParams['objfile-index'] = self._calcObjectsIndex(bconf, taskParams)

    def _setupTaskTarget(self, taskParams, taskEnv, btypeDir):

        features = taskParams['features']
        targetKind = lang = None
        for feature in features:
            lang = TASK_TARGET_FEATURES_TO_LANG.get(feature)
            if lang is not None:
                targetKind = feature[len(lang):]
                break
        taskParams['$tlang'] = lang
        taskParams['$tkind'] = targetKind

        patterns = {}
        if lang:
            for kind in TASK_TARGET_KINDS:
                key = '%s%s_PATTERN' % (lang, kind)
                pattern = taskEnv[key]
                if pattern:
                    patterns[kind] = pattern
        taskParams['$tpatterns'] = patterns

        taskName = taskParams['name']

        normalizeTarget = taskParams.get('normalize-target-name', False)
        target = taskParams.get('target', taskName)
        if normalizeTarget:
            target = utils.normalizeForFileName(target, spaceAsDash = True)
        targetPath = joinpath(btypeDir, target)
        taskParams['target'] = targetPath

        env = self.all_envs[taskParams['$task.variant']]
        pattern = patterns.get(targetKind)
        realTarget = assist.makeTargetRealName(targetPath, targetKind, pattern,
                                               env, taskParams.get('ver-num'))

        taskParams['$real.target'] = realTarget
        taskParams['$runnable'] = targetKind == 'program'

    def _preconfigureTasks(self, bconf):

        buildtype = bconf.selectedBuildType
        btypeDir = bconf.selectedBuildTypeDir
        tasks = bconf.tasks
        prjver = bconf.projectVersion

        emptyEnv = ConfigSet()
        toolchainEnvs = self.getToolchainEnvs()

        for taskParams in viewvalues(tasks):

            taskName = taskParams['name']

            # make variant name for each task: 'buildtype.taskname'
            taskVariant = assist.makeTaskVariantName(buildtype, taskName)
            # store it
            taskParams['$task.variant'] = taskVariant

            # set up env with toolchain for task
            _toolchains = taskParams['toolchain']
            if _toolchains:
                baseEnv = toolchainEnvs[_toolchains[0]]
                if len(_toolchains) > 1:
                    # make copy of env to avoid using 'update' on original
                    # toolchain env
                    baseEnv = assist.copyEnv(baseEnv)
                for toolname in _toolchains[1:]:
                    baseEnv.update(toolchainEnvs[toolname])
            else:
                needToolchain = set(taskParams['features']) & TASK_LANG_FEATURES
                if needToolchain:
                    msg = "No toolchain for task %r found." % taskName
                    msg += " Is buildconf correct?"
                    self.fatal(msg)
                else:
                    baseEnv = emptyEnv

            # Create env for task
            taskEnv = assist.deepcopyEnv(baseEnv)

            # conf.setenv with unknown name or non-empty env makes deriving or
            # creates the new object and it is not really needed here
            self.setDirectEnv(taskVariant, taskEnv)

            if prjver and 'ver-num' not in taskParams:
                taskParams['ver-num'] = prjver

            self._setupTaskTarget(taskParams, taskEnv, btypeDir)

    def preconfigure(self):
        """
        Pre configure. It's called by 'execute' before call of actual 'configure'.
        """

        configs = self.bconfManager.configs

        for bconf in configs:

            # set context path
            self.path = self.getPathNode(bconf.confdir)

            # it's necessary to handle 'toolchain.select' before loading of toolchains
            for taskParams in viewvalues(bconf.tasks):
                handleOneTaskParamSelect(bconf, taskParams, 'toolchain')

            # load all toolchains envs
            self.loadToolchains(bconf)

            # Other '*.select' params must be handled after loading of toolchains
            handleTaskParamSelects(bconf)

        toolchainEnvs = self.getToolchainEnvs()

        # Remove toolchain envs from self.all_envs
        # to avoid potential name conflicts and to free mem
        for toolchain in viewkeys(toolchainEnvs):
            self.all_envs.pop(toolchain, None)

        # set/fix vars PREFIX, BINDIR, LIBDIR
        assist.applyInstallPaths(self.all_envs[''], cli.selected)

        for bconf in configs:
            self._preconfigureTasks(bconf)

        # switch current env to the root env
        self.setenv('')

    # override
    def execute(self):

        bconf = self.bconfManager.root
        bconfPaths = bconf.confPaths

        # See details here: https://gitlab.com/ita1024/waf/issues/1563
        self.env.NO_LOCK_IN_RUN = True
        self.env.NO_LOCK_IN_TOP = True

        self.init_dirs()

        self.cachedir = self.bldnode.make_node(WAF_CACHE_DIRNAME)
        self.cachedir.mkdir()

        if bconfPaths.zmcachedir != self.cachedir.abspath():
            try:
                os.makedirs(bconfPaths.zmcachedir)
            except OSError:
                pass

        path = joinpath(self.bldnode.abspath(), WAF_CONFIG_LOG)
        self.logger = log.makeLogger(path, 'cfg')

        projectDesc = "%s (ver: %s)" % (bconf.projectName, bconf.projectVersion)
        pyDesc = "%s (%s)" % (platform.python_version(), platform.python_implementation())

        cliArgs = [sys.argv[0]] + cli.selected.orig
        confHeaderParams = {
            'now'     : time.ctime(),
            'zmver'   : version.current(),
            'wafver'  : WafContext.WAFVERSION,
            'wafabi'  : WafContext.ABI,
            'pyver'   : pyDesc,
            'systype' : sys.platform,
            'args'    : " ".join(cliArgs),
            'prj'     : projectDesc,
        }

        self.to_log(CONFLOG_HEADER_TEMPLATE % confHeaderParams)
        self.msg('Setting top to', self.srcnode.abspath())
        self.msg('Setting out to', self.bldnode.abspath())

        if id(self.srcnode) == id(self.bldnode):
            log.warn('Setting startdir == buildout')
        elif id(self.path) != id(self.srcnode):
            if self.srcnode.is_child_of(self.path):
                log.warn('Are you certain that you do not want to set top="." ?')

        self.loadCaches()
        self.preconfigure()

        produceExternalDeps(self)
        WafContext.Context.execute(self)

        self._mergeTasks()
        self._postCheckTasks()
        self.store()

        instanceCache = self.zmcache()
        bconfPathsAdded = instanceCache.get('confpaths-added-to-monit', False)
        if not bconfPathsAdded:
            self.monitFiles.extend([x.path for x in self.bconfManager.configs])
            instanceCache['confpaths-added-to-monit'] = True

        WafContext.top_dir = self.srcnode.abspath()
        WafContext.out_dir = self.bldnode.abspath()

        self.zmMetaConfAttrs.update({
            'last-python-ver': '.'.join(str(x) for x in sys.version_info[:3]),
            'last-dbformat': db.getformat(),
        })
        zmmetafile = bconfPaths.zmmetafile
        assist.writeZenMakeMetaFile(zmmetafile, self.monitFiles,
                                    self.zmMetaConfAttrs)
