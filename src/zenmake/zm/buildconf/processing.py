# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from collections import defaultdict
from copy import deepcopy

from zm.constants import PLATFORM, KNOWN_PLATFORMS
from zm.constants import CWD, INVALID_BUILDTYPES, CONFTEST_DIR_PREFIX
from zm.autodict import AutoDict
from zm.error import ZenMakeError, ZenMakeLogicError, ZenMakeConfError
from zm.pyutils import stringtype, maptype, viewitems, viewvalues
from zm import utils, log
from zm.buildconf import loader
from zm.buildconf.scheme import KNOWN_CONF_PARAM_NAMES
from zm.features import ToolchainVars

joinpath = os.path.join
abspath  = os.path.abspath
normpath = os.path.normpath
dirname  = os.path.dirname
relpath  = os.path.relpath
isabs    = os.path.isabs
isdir    = os.path.isdir

toList = utils.toList

#def _isDevVersion():
#    """
#    Detect if it is development version of the ZenMake
#    """
#    from zm import version
#    return version.isDev()

class Config(object):
    """
    Class to get/process data from the certain buildconf module
    """

    #pylint: disable=too-many-public-methods

    __slots__ = '_conf', '_meta', '_confpaths', '_parent'

    def __init__(self, buildconf, buildroot = None, parent = None):
        """
        buildconf - module of a buildconf file
        buildroot - forced buildroot (from cmdline)
        parent    - parent Config object
        """

        self._parent = parent
        self._conf = buildconf

        self._meta = AutoDict()
        self._meta.buildtypes.selected = None

        # independent own dir paths
        self._meta.buildconffile = abspath(buildconf.__file__)
        self._meta.buildconfdir  = dirname(self._meta.buildconffile)
        self._makeStartDirParam()
        self._meta.rootdir = parent.rootdir if parent else self._meta.startdir

        # init/merge params including values from parent Config
        self._applyDefaults()
        self._postValidateConf()
        self._makeBuildDirParams(buildroot)
        self._fixStartDirForConfPathParams()
        self._handleTaskNames() # must be called before merging
        self._merge()

        from zm.buildconf.paths import ConfPaths
        self._confpaths = ConfPaths(self)

    def _makeStartDirParam(self):
        buildconf = self._conf
        meta = self._meta
        try:
            startdir = utils.getNativePath(buildconf.startdir)
        except AttributeError:
            startdir = os.curdir
        meta.startdir = utils.unfoldPath(meta.buildconfdir, startdir)
        setattr(buildconf, 'startdir', meta.startdir)

    def _makeBuildDirParams(self, buildroot):
        #pylint: disable=protected-access

        # Get 'buildroot' and 'realbuildroot' from parent
        # if that exists or from current.
        # If param buildroot from func args is not None then it overrides
        # the same param from buildconf.

        currentConf = self._conf
        srcbconf = self._parent if self._parent else self

        def mergeBuildRoot(param):
            value = getattr(srcbconf._conf, param)
            value = utils.getNativePath(value)
            value = utils.unfoldPath(srcbconf.startdir, value)
            setattr(currentConf, param, value)

        if buildroot and not self._parent:
            buildroot = utils.getNativePath(buildroot)
            buildroot = utils.unfoldPath(self.startdir, buildroot)
            setattr(currentConf, 'buildroot', buildroot)
        else:
            mergeBuildRoot('buildroot')

        if not hasattr(srcbconf._conf, 'realbuildroot'):
            setattr(srcbconf._conf, 'realbuildroot', currentConf.buildroot)
        else:
            mergeBuildRoot('realbuildroot')

    def _fixStartDirForConfPathParams(self):

        buildconf = self._conf
        startdir = self.startdir

        def fixSrcParam(taskparams, startdir):
            param = taskparams.get('source', None)
            if not param:
                return
            if isinstance(param, maptype):
                param['startdir'] = startdir
            else:
                param = dict(startdir = startdir, paths = param)
                taskparams['source'] = param
            # premake lists to avoid conversions later
            for arg in ('include', 'exclude', 'paths'):
                if arg in param:
                    param[arg] = tuple(toList(param[arg]))

        def fixPathParam(taskparams, paramname, startdir):
            param = taskparams.get(paramname, None)
            if param is None:
                return
            taskparams[paramname] = dict(startdir = startdir, paths = param)

        def fixRunParam(taskparams, startdir):
            param = taskparams.get('run', None)
            if not param:
                return
            param['startdir'] = startdir

        def fixTaskParams(taskparams, startdir):
            # 'source'
            fixSrcParam(taskparams, startdir)
            # 'includes'
            fixPathParam(taskparams, 'includes', startdir)
            fixPathParam(taskparams, 'export-includes', startdir)
            # 'libpath'
            fixPathParam(taskparams, 'libpath', startdir)
            # 'run'
            fixRunParam(taskparams, startdir)

        # tasks, buildtypes
        for varName in ('tasks', 'buildtypes'):
            confVar = getattr(buildconf, varName)
            for taskparams in viewvalues(confVar):
                if not isinstance(taskparams, maptype):
                    # buildtypes has special key 'default'
                    continue
                fixTaskParams(taskparams, startdir)

        # matrix
        for entry in buildconf.matrix:
            fixTaskParams(entry.get('set', {}), startdir)

        # 'toolchains'
        for params in viewvalues(buildconf.toolchains):
            for k, v in viewitems(params):
                if k == 'kind':
                    continue
                param = utils.getNativePath(v)
                if not isabs(param):
                    params[k] = utils.unfoldPath(startdir, v)

    def _fixTaskPathParamsToStartDir(self, tasks):

        # they are absolute paths
        rootdir = self.rootdir
        startdir = self.startdir

        # make 'startdir' for task and specific params as
        # the paths relative to the 'rootdir'
        taskStartDir = relpath(startdir, rootdir)
        for taskParams in viewvalues(tasks):
            taskParams['$startdir'] = taskStartDir
            for param in viewvalues(taskParams):
                if not isinstance(param, maptype):
                    continue
                paramStartDir = param.get('startdir', None)
                if paramStartDir is None:
                    continue
                if paramStartDir == startdir:
                    param['startdir'] = taskStartDir
                else:
                    param['startdir'] = relpath(paramStartDir, rootdir)

    def _merge(self):

        #pylint: disable=protected-access

        mergedParams = set()
        currentConf = self._conf
        parentConf = self._parent._conf if self._parent else None

        def mergeDict(param):
            if not parentConf:
                return
            _current = getattr(currentConf, param, {})
            _parent = getattr(parentConf, param, {})
            _new = _parent.copy()
            for k, v in viewitems(_current):
                if isinstance(v, maptype):
                    _new.setdefault(k, {})
                    _new[k].update(v)
                else:
                    _new[k] = v

            setattr(currentConf, param, _new)

        # startdir, options, subdirs - they are not merged
        mergedParams.update(('startdir', 'options', 'subdirs'))

        # buildroot, realbuildroot - see _makeBuildDirParams
        mergedParams.update(('buildroot', 'realbuildroot'))

        # project, features
        for param in ('project', 'features'):
            mergeDict(param)
            mergedParams.add(param)

        # tasks - it's not merged
        mergedParams.add('tasks')

        # buildtypes, toolchains, platforms
        for param in ('buildtypes', 'toolchains', 'platforms'):
            mergeDict(param)
            mergedParams.add(param)

        # matrix
        if parentConf:
            # append the parentConf.matrix to the front of the currentConf.matrix
            currentConf.matrix[0:0] = parentConf.matrix
        mergedParams.add('matrix')

        #TODO: move to tests
        # check all params were processed
        assert mergedParams == KNOWN_CONF_PARAM_NAMES

    def _applyDefaults(self):
        """
        Set default values to some params in buildconf if they don't exist
        """

        loader.applyDefaults(self._conf, not self._parent, self.rootdir)

    def _postValidateConf(self):

        # check buildtype names

        matrixBuildTypes = self._getMatrixBuildtypes()
        buildtypes = list(matrixBuildTypes.keys())
        buildtypes.extend(self._conf.buildtypes.keys())
        buildtypes = tuple(set(buildtypes)) # make unique list
        for buildtype in buildtypes:
            if buildtype in INVALID_BUILDTYPES or buildtype.startswith(CONFTEST_DIR_PREFIX):
                msg = "Error in the buildconf file %r:" % relpath(self.path, CWD)
                msg += "\nName %r is invalid for a buildtype." % buildtype
                msg += " Set a different name."
                raise ZenMakeError(msg)

    def _handleTaskNames(self):

        names = list(self._conf.tasks.keys())
        for entry in self._conf.matrix:
            names.extend(toList(entry.get('for', {}).get('task', [])))
        names = set(names)
        self._meta.tasknames = names

    def _handleTasksEnvVars(self, tasks):

        flagVars      = ToolchainVars.allFlagVars()
        toolchainVars = ToolchainVars.allVarsToSetToolchain()

        for taskParams in viewvalues(tasks):
            # handle flags
            for var in flagVars:
                envVal = os.environ.get(var, None)
                if not envVal:
                    continue

                paramName = var.lower()

                #current = toList(taskParams.get(paramName, []))
                # FIXME: should we add or replace? change docs on behavior change
                #taskParams[paramName] = current + toList(envVal)
                taskParams[paramName] = toList(envVal)

            # handle toolchains
            for var in toolchainVars:
                toolchain = os.environ.get(var, None)
                if not toolchain:
                    continue
                if var.lower() in taskParams.get('features', ''):
                    taskParams['toolchain'] = toolchain

    def _handleMatrixBuildtypes(self):
        destPlatform = PLATFORM
        matrixBuildTypes = defaultdict(set)

        def handleCondition(entry, name):
            condition = entry.get(name, {})
            buildtypes = toList(condition.get('buildtype', []))
            platforms = toList(condition.get('platform', []))

            if buildtypes:
                if not platforms:
                    matrixBuildTypes['all'].update(buildtypes)
                elif name == 'for' and destPlatform in platforms:
                    matrixBuildTypes[destPlatform].update(buildtypes)
                elif name == 'not-for' and destPlatform not in platforms:
                    matrixBuildTypes[destPlatform].update(buildtypes)

            return platforms

        for entry in self._conf.matrix:

            enabledPlatforms = handleCondition(entry, 'for')
            disabledPlatforms = handleCondition(entry, 'not-for')

            defaultBuildType = entry.get('set', {}).get('default-buildtype', None)
            if defaultBuildType is not None:
                if not enabledPlatforms:
                    enabledPlatforms = KNOWN_PLATFORMS

                enabledPlatforms = set(enabledPlatforms) - set(disabledPlatforms)
                if destPlatform in enabledPlatforms:
                    matrixBuildTypes['default'] = defaultBuildType

        self._meta.matrix.buildtypes = matrixBuildTypes

    def _getMatrixBuildtypes(self):

        matrix = self._meta.matrix
        if 'buildtypes' not in matrix:
            self._handleMatrixBuildtypes()
            assert 'buildtypes' in matrix

        return matrix.buildtypes

    def _handleSupportedBuildTypes(self):
        """
        Calculate list of supported build types
        """

        destPlatform = PLATFORM

        supported = set()
        matrixBuildTypes = self._getMatrixBuildtypes()

        platformFound = False
        platforms = self._conf.platforms
        if destPlatform in platforms:
            platformFound = True
            supported = platforms[destPlatform].get('valid', [])
            supported = toList(supported)
        else:
            supported = self._conf.buildtypes.keys()
        supported = set(supported)

        if destPlatform in matrixBuildTypes:
            platformFound = True
            supported.update(matrixBuildTypes[destPlatform])

        supported.update(matrixBuildTypes.get('all', set()))

        if 'default' in supported:
            supported.remove('default')

        if platformFound and not supported:
            raise ZenMakeConfError("No valid build types for platform '%s' "
                                   "in config" % destPlatform)

        if not supported:
            # empty buildtype if others aren't detected
            supported = set([''])

        self._meta.buildtypes.supported = sorted(supported)

    def _handleDefaultBuildType(self):
        """ Calculate default build type """

        platforms = self._conf.platforms
        buildtype = self._conf.buildtypes.get('default', None)
        if PLATFORM in platforms:
            buildtype = platforms[PLATFORM].get('default', buildtype)

        matrixBuildTypes = self._getMatrixBuildtypes()
        buildtype = matrixBuildTypes.get('default', buildtype)

        supportedBuildTypes = self.supportedBuildTypes
        if buildtype is None:
            if len(supportedBuildTypes) == 1:
                buildtype = supportedBuildTypes[0]
            else:
                buildtype = ''

        if buildtype not in supportedBuildTypes:
            errmsg = "Default build type '%s'" % buildtype
            if 'default' in matrixBuildTypes:
                errmsg += " from the config variable 'matrix'"
            elif PLATFORM in platforms and 'default' in platforms[PLATFORM]:
                errmsg += " from the config variable 'platform'"
            else:
                errmsg += " from the config variable 'buildtypes'"
            errmsg += " is invalid\nfor the current supported values."
            supportedValues = str(supportedBuildTypes)[1:-1]
            if not supportedValues:
                supportedValues = "\nNo supported values. Check buildconf."
            else:
                supportedValues = "\nSupported values: %s." % supportedValues
            errmsg += supportedValues
            raise ZenMakeConfError(errmsg)

        self._meta.buildtypes.default = buildtype

    def _checkBuildTypeIsSet(self):
        if self._meta.buildtypes.selected is None:
            raise ZenMakeLogicError("Command line buildtype wasn't applied yet. "
                                    "You should call method applyBuildType.")

    def applyBuildType(self, buildtype):
        """
        Apply buildtype from command line
        """

        supportedBuildTypes = self.supportedBuildTypes
        isNotValidType = not isinstance(buildtype, stringtype)
        isNotSupported = self.taskNames and buildtype not in supportedBuildTypes
        if isNotValidType or isNotSupported:
            supportedBuildTypes = str(supportedBuildTypes)[1:-1]
            msg = "Invalid build type: '%s'" % buildtype
            confFile = relpath(self.path, CWD)
            if not supportedBuildTypes:
                msg += ". No supported buildtypes for config %r." % confFile
            else:
                msg += " for config %r,\nChoose from: [%s]" % \
                       (confFile, supportedBuildTypes)
            raise ZenMakeError(msg)

        self._meta.buildtypes.selected = buildtype
        self._meta.buildtype.dir = joinpath(self._confpaths.buildout, buildtype)

    def getattr(self, name, **kwargs):
        """
        getattr(name[, default]) -> value, bconf

        Get a named attribute from the current or parent buildconf;
        If the named attribute does not exist, default is returned if provided,
        otherwise AttributeError is raised.

        Returns pair (value, bconf) where bconf is the Config object from
        which the found value.
        """

        #pylint: disable=protected-access

        def getValue(name):
            attr = self._meta.getattr[name]
            if not attr.exists:
                if 'default' in kwargs:
                    return kwargs['default'], None
                raise AttributeError("'buildconf' has no attribute %r" % name)
            return attr.value, attr.bconf

        if name in self._meta.getattr:
            return getValue(name)

        exists = False
        result = None
        config = self
        while config:
            try:
                result = getattr(config._conf, name)
            except AttributeError:
                pass
            else:
                exists = True
                break

            config = config._parent

        self._meta.getattr[name] = AutoDict(
            exists = exists,
            value = result,
            bconf = config,
        )
        return getValue(name)

    @property
    def parent(self):
        """ Get parent Config. Returns None if no parent"""
        return self._parent

    @property
    def taskNames(self):
        """
        Get all task names from the current config.
        Returns set of names.
        """

        return self._meta.tasknames

    @property
    def projectName(self):
        """ Get project name """
        return self._conf.project['name']

    @property
    def projectVersion(self):
        """ Get project version """
        return self._conf.project['version']

    @property
    def options(self):
        """ Get default options for cli from buildconf """
        return self._conf.options

    @property
    def confPaths(self):
        """ Get object of class buildconf.paths.ConfPaths """
        return self._confpaths

    @property
    def path(self):
        """ Get path of the conf file"""
        return self._meta.buildconffile

    @property
    def confdir(self):
        """ Get dir path of the conf file"""
        return self._meta.buildconfdir

    @property
    def startdir(self):
        """
        Get startdir for the conf file.
        It's always absolute path.
        """
        return self._meta.startdir

    @property
    def rootdir(self):
        """
        Get startdir of the top-level conf file.
        It's always absolute path.
        """
        return self._meta.rootdir

    @property
    def defaultBuildType(self):
        """ Get calculated default build type """

        buildtypes = self._meta.buildtypes
        if 'default' not in buildtypes:
            self._handleDefaultBuildType()
            assert 'default' in buildtypes

        return buildtypes.default

    @property
    def selectedBuildType(self):
        """ Get selected build type """

        self._checkBuildTypeIsSet()
        return self._meta.buildtypes.selected

    @property
    def selectedBuildTypeDir(self):
        """ Get selected build type directory """

        self._checkBuildTypeIsSet()
        return self._meta.buildtype.dir

    @property
    def features(self):
        """ Get features """
        return self._conf.features

    @property
    def subdirs(self):
        """ Get correct 'subdirs' from the buildconf """

        if 'subdirs' in self._meta:
            return self._meta.subdirs

        try:
            subdirs = self._conf.subdirs
        except AttributeError:
            subdirs = None

        if not subdirs:
            subdirs = []

        def fixpath(bconfdir, path):
            path = utils.getNativePath(path)
            if not isabs(path):
                path = joinpath(bconfdir, path)
            return path

        bconfdir = self.confdir
        dirs = [fixpath(bconfdir, x) for x in subdirs]

        for i, fullpath in enumerate(dirs):
            if not isdir(fullpath):
                msg = "Error in the buildconf file %r:" % relpath(self.path, CWD)
                msg += "\nDirectory %r from the 'subdirs' doesn't exist." % subdirs[i]
                raise ZenMakeError(msg)

        subdirs = dirs
        self._meta.subdirs = subdirs
        return subdirs

    @property
    def supportedBuildTypes(self):
        """ Get calculated list of supported build types """

        buildtypes = self._meta.buildtypes
        if 'supported' not in buildtypes:
            self._handleSupportedBuildTypes()
            assert 'supported' in buildtypes

        return buildtypes.supported

    @property
    def tasks(self):
        """
        Get all build tasks
        """

        self._checkBuildTypeIsSet()

        buildtype = self.selectedBuildType
        if buildtype in self._meta.tasks:
            return self._meta.tasks[buildtype]

        knownPlatforms = set(KNOWN_PLATFORMS)
        allTaskNames = self.taskNames
        destPlatform = PLATFORM

        tasks = {}

        for taskName in tuple(allTaskNames):

            task = tasks.setdefault(taskName, {})
            # 1. Copy existing params from origin task
            task.update(self._conf.tasks.get(taskName, {}))
            # 2. Copy/replace exising params of selected buildtype from 'buildtypes'
            task.update(self._conf.buildtypes.get(buildtype, {}))

        def getMatrixCondition(entry, name):
            condition = entry.get(name, None)
            result = dict( condition = condition )

            if condition is None:
                if name == 'for':
                    result['tasks'] = allTaskNames
                else: # if name == 'not-for'
                    assert name == 'not-for'
                    result['tasks'] = set()
                return result

            buildtypes = set(toList(condition.get('buildtype', [])))
            platforms = set(toList(condition.get('platform', [])))
            tasks = set(toList(condition.get('task', [])))

            if not platforms:
                platforms = knownPlatforms
            if not buildtypes:
                buildtypes = self.supportedBuildTypes

            if destPlatform in platforms and buildtype in buildtypes:
                if not tasks:
                    tasks = set(allTaskNames)
                tasks &= allTaskNames # use tasks from current config only
                result['tasks'] = tasks
            else:
                result['tasks'] = set()

            return result

        for entry in self._conf.matrix:

            enabled = getMatrixCondition(entry, 'for')
            disabled = getMatrixCondition(entry, 'not-for')

            if enabled['condition'] is None and disabled['condition'] is None:
                log.warn("WARN: buildconf.matrix has an item without 'for' and 'not-for'. "
                         "It's probably a mistake.")

            enabledTasks = tuple(enabled['tasks'])
            disabledTasks = disabled['tasks']
            params = entry.get('set', {})

            for taskName in enabledTasks:
                if taskName in disabledTasks:
                    continue
                task = tasks.setdefault(taskName, {})
                task.update(params)
                task.pop('default-buildtype', None)

        self._fixTaskPathParamsToStartDir(tasks)
        self._handleTasksEnvVars(tasks)

        self._meta.tasks[buildtype] = tasks
        return tasks

    @property
    def customToolchains(self):
        """
        Get 'custom' toolchains.
        """

        if 'custom' in self._meta.toolchains:
            return self._meta.toolchains.custom

        srcToolchains = self._conf.toolchains
        _customToolchains = AutoDict()
        for name, info in viewitems(srcToolchains):
            _vars = deepcopy(info) # don't change origin
            kind = _vars.pop('kind', None)
            if kind is None:
                raise ZenMakeConfError("Toolchain '%s': field 'kind' not found" % name)

            for k, v in viewitems(_vars):
                # try to identify path and do warning if not
                path = utils.unfoldPath(self.startdir, v)
                if not os.path.exists(path):
                    log.warn("Path to toolchain '%s' doesn't exist" % path)
                _vars[k] = path

            _customToolchains[name].kind = kind
            _customToolchains[name].vars = _vars

        self._meta.toolchains.custom = _customToolchains
        return _customToolchains

class ConfManager(object):
    """
    Class to manage Config instances
    """

    __slots__ = '_buildroot', '_configs', '_virtConfigs', '_orderedConfigs'

    def __init__(self, topdir, buildroot):
        topdir = abspath(topdir)
        # forced buildroot (from cmdline)
        self._buildroot = buildroot

        self._orderedConfigs = []
        self._configs = {}
        self._virtConfigs = {}

        rootConfig = self.makeConfig(topdir, buildroot = buildroot)
        self._makeSubConfigs(rootConfig)

    def _makeSubConfigs(self, bconf):
        subdirs = bconf.subdirs
        for subdir in subdirs:
            subconf = self.makeConfig(subdir, parent = bconf)
            self._makeSubConfigs(subconf)

    def makeConfig(self, dirpath, buildroot = None, parent = None):
        """
        Make Config object for dirpath.
        """

        filename = loader.findConfFile(dirpath)
        if not filename:
            msg = 'No buildconf.py/.yaml found in the directory %r' \
                  % relpath(dirpath, CWD)
            raise ZenMakeError(msg)

        buildconf = loader.load(dirpath, filename)

        #TODO: optimize to validate only if buildconf files were changed
        #if assist.isBuildConfChanged(buildconf, buildroot) or _isDevVersion():
        #    loader.validate(buildconf)
        loader.validate(buildconf)

        index = len(self._orderedConfigs)
        self._configs[dirpath] = index

        bconf = Config(buildconf, buildroot, parent)
        self._orderedConfigs.append(bconf)
        startdir = bconf.startdir
        if startdir != dirpath:
            self._virtConfigs[startdir] = index

        return bconf

    @property
    def root(self):
        """
        Get root/origin Config.
        Returns None if no valid buildconf was found.
        """
        return self._orderedConfigs[0]

    @property
    def configs(self):
        """
        Get list of all configs with preserved order
        """
        return self._orderedConfigs

    def configIndex(self, dirpath):
        """
        Get index of Config object by dirpath.
        Return None if not found
        """

        index = self._configs.get(dirpath, None)
        if index is None:
            index = self._virtConfigs.get(dirpath, None)
        return index

    def config(self, dirpath):
        """
        Get Config object for dirpath. Parameter dirpath can the 'startdir' for
        buildconf or just directory with buildconf file.
        Returns None if config was not found for the dirpath.
        """

        # It always must be an absolute norm path to avoid duplicates
        dirpath = abspath(dirpath)

        index = self.configIndex(dirpath)
        if index is None:
            return None

        return self._orderedConfigs[index]
