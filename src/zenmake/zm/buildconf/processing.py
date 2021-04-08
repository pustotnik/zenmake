# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import re
from collections import defaultdict
from copy import deepcopy

from zm.constants import PLATFORM, KNOWN_PLATFORMS, DEPNAME_DELIMITER
from zm.constants import CWD, INVALID_BUILDTYPES, CONFTEST_DIR_PREFIX
from zm.autodict import AutoDict
from zm.error import ZenMakeError, ZenMakeLogicError, ZenMakeConfError
from zm.pyutils import stringtype, maptype
from zm import utils, log
from zm.pathutils import unfoldPath, getNativePath
from zm.pathutils import PathsParam, makePathsConf
from zm.buildconf import loader
from zm.buildconf.scheme import taskscheme, KNOWN_CONF_PARAM_NAMES
from zm.features import ToolchainVars, BUILDCONF_PREPARE_TASKPARAMS

joinpath = os.path.join
abspath  = os.path.abspath
normpath = os.path.normpath
dirname  = os.path.dirname
relpath  = os.path.relpath
isabs    = os.path.isabs
isdir    = os.path.isdir

toList        = utils.toList
toListSimple  = utils.toListSimple

TOOLCHAIN_PATH_ENVVARS = frozenset(ToolchainVars.allSysVarsToSetToolchain())
_RE_LIB_VER = re.compile(r"^\d+(?:\.\d+)*")

_TASKPARAMS_TOLIST_MAP = {}

#def _isDevVersion():
#    """
#    Detect if it is development version of the ZenMake
#    """
#    from zm import version
#    return version.isDev()

def _applyStartDirToParam(bconf, param):
    if isinstance(param, bool):
        return param
    return PathsParam(param, bconf.startdir, kind = 'paths')

_PREPARE_TASKPARAMS_HOOKS = [(x, _applyStartDirToParam)
                             for x in ('includes', 'export-includes', 'libpath', 'stlibpath')]

_PREPARE_TASKPARAMS_HOOKS = tuple(_PREPARE_TASKPARAMS_HOOKS) + \
                            BUILDCONF_PREPARE_TASKPARAMS

def _genTaskParamsToListMap(result):

    skipNames = ('configure', 'name', 'install-files')
    for name, scheme in taskscheme.items():
        if name in skipNames or name.endswith('.select'):
            continue
        types = scheme['type']
        if 'str' in types and 'list-of-strs' in types:
            if name.endswith('flags'):
                result[name] = toListSimple
            else:
                result[name] = toList

    # Value 'None' means: don't make a list
    result.update({
        'name' : None,
        'features' : toListSimple,
        'configure' : None,
        'install-files' : None, # all convertions are in commands install/uninstall
    })
    return result

def convertTaskParamValue(taskParams, paramName):
    """
    Convert task param value to list or to dict with correct structure
    where it's necessary.
    """

    paramVal = taskParams[paramName]

    if paramName == 'source':
        startdir = taskParams['$bconf'].startdir
        taskParams[paramName] = makePathsConf(paramVal, startdir)
        return

    if paramName.endswith('.select'):
        return

    if not _TASKPARAMS_TOLIST_MAP:
        _genTaskParamsToListMap(_TASKPARAMS_TOLIST_MAP)

    _toList = _TASKPARAMS_TOLIST_MAP.get(paramName)
    if _toList is not None:
        taskParams[paramName] = _toList(paramVal)

class Config(object):
    """
    Class to get/process data from the certain buildconf module
    """

    # pylint: disable = too-many-public-methods

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
        self._prepareParams()
        self._handleTaskNames() # must be called before merging
        self._merge()

        from zm.buildconf.paths import ConfPaths
        self._confpaths = ConfPaths(self)

    def _makeStartDirParam(self):
        buildconf = self._conf
        meta = self._meta
        try:
            startdir = getNativePath(buildconf.startdir)
        except AttributeError:
            startdir = os.curdir
        meta.startdir = unfoldPath(meta.buildconfdir, startdir)
        buildconf.startdir = meta.startdir

    def _makeBuildDirParams(self, buildroot):
        # pylint: disable = protected-access

        # Get 'buildroot' and 'realbuildroot' from parent
        # if they exist or from current.
        # If param buildroot from func args is not None then it overrides
        # the same param from buildconf.

        currentConf = self._conf
        srcbconf = self._parent if self._parent else self

        def mergeBuildRoot(param):
            value = getattr(srcbconf._conf, param)
            value = unfoldPath(srcbconf.startdir, getNativePath(value))
            setattr(currentConf, param, value)

        if buildroot and not self._parent:
            buildroot = unfoldPath(self.startdir, getNativePath(buildroot))
            currentConf.buildroot = buildroot
        else:
            mergeBuildRoot('buildroot')

        if not hasattr(srcbconf._conf, 'realbuildroot'):
            srcbconf._conf.realbuildroot = currentConf.buildroot
        else:
            mergeBuildRoot('realbuildroot')

    def _prepareTaskParams(self):

        buildconf = self._conf
        startdir = self.startdir

        def prepareTaskParams(hooks, taskparams):

            for hookInfo in hooks:
                paramName = hookInfo[0]
                handler   = hookInfo[1]
                param = taskparams.get(paramName)
                if param is not None:
                    taskparams[paramName] = handler(self, param)

                paramName += '.select'
                param = taskparams.get(paramName, {})
                for condition in param:
                    param[condition] = handler(self, param[condition])

        # tasks, buildtypes
        for varName in ('tasks', 'buildtypes'):
            confVar = getattr(buildconf, varName)
            for taskparams in confVar.values():
                if not isinstance(taskparams, maptype):
                    # buildtypes has special key 'default'
                    continue
                prepareTaskParams(_PREPARE_TASKPARAMS_HOOKS, taskparams)

        # byfilter
        for entry in buildconf.byfilter:
            taskparams = entry.get('set')
            if taskparams:
                prepareTaskParams(_PREPARE_TASKPARAMS_HOOKS, taskparams)

        # 'toolchains'
        for params in buildconf.toolchains.values():
            for k, v in params.items():
                if k not in TOOLCHAIN_PATH_ENVVARS:
                    continue
                params[k] = unfoldPath(startdir, getNativePath(v))

    def _prepareParams(self):

        startdir = self.startdir
        relStartDir = relpath(startdir, self.rootdir)

        def makePathParam(param, name, kind):
            value = param.get(name)
            if value:
                param[name] = PathsParam(value, startdir, kind)
            else:
                param.pop(name, None)

        def _makePathParamWithPattern(param, name):
            value = param.get(name)
            if value:
                param[name] = makePathsConf(value, relStartDir)
            else:
                param.pop(name, None)

        # features
        confFeatures = self._conf.features
        makePathParam(confFeatures, 'monitor-files', kind = 'paths')

        # external dependencies
        for dep in self._conf.edeps.values():
            makePathParam(dep, 'rootdir', kind = 'path')
            makePathParam(dep, 'export-includes', kind = 'paths')

            targets = dep.get('targets', {})
            for params in targets.values():
                makePathParam(params, 'dir', kind = 'path')

            rules = dep.get('rules', {})
            for params in rules.values():
                if not isinstance(params, maptype):
                    continue
                makePathParam(params, 'cwd', kind = 'path')

                triggers = params.get('trigger', {})
                _makePathParamWithPattern(triggers, 'paths-exist')
                _makePathParamWithPattern(triggers, 'paths-dont-exist')
                func = triggers.get('func')
                if func:
                    triggers['func'] = (self.confdir, func.__name__)

        # taskparams
        self._prepareTaskParams()

    def _postprocessTaskParams(self, tasks):

        # they are absolute paths
        rootdir = self.rootdir
        startdir = self.startdir

        rootSubstVars = getattr(self._conf, 'substvars', {})

        # make 'startdir' for task and specific params as
        # the paths relative to the 'rootdir'
        taskStartDir = relpath(startdir, rootdir)

        disabled = []

        for taskName, taskParams in tasks.items():

            if not taskParams.get('enabled', True):
                disabled.append(taskName)
                continue

            # save task name in task params
            taskParams['name'] = taskName

            # set startdir and bconf in task params
            taskParams['$startdir'] = taskStartDir
            taskParams['$bconf'] = self

            for paramName, paramVal in taskParams.items():

                taskParams[paramName] = paramVal
                convertTaskParamValue(taskParams, paramName)

                if paramName != 'source':
                    continue

                # set relative startdir, just to reduce size of build cache
                paramVal = taskParams[paramName]
                for item in paramVal:
                    paramStartDir = item['startdir']
                    if utils.hasSubstVar(paramStartDir):
                        # don't touch 'startdir' if it has subst var
                        continue
                    if paramStartDir == startdir:
                        item['startdir'] = taskStartDir
                    elif isabs(paramStartDir):
                        item['startdir'] = relpath(paramStartDir, rootdir)

            substVars = rootSubstVars.copy()
            substVars.update(taskParams.get('substvars', {}))
            if substVars:
                taskParams['substvars'] = substVars

        tasknames = self._meta.tasknames
        for name in disabled:
            tasknames.remove(name)
            tasks.pop(name)

    def _merge(self):

        # pylint: disable = protected-access

        mergedParams = set()
        currentConf = self._conf
        parentConf = self._parent._conf if self._parent else None

        def mergeDict(param):
            if parentConf is None:
                return
            _current = getattr(currentConf, param, {})
            _parent = getattr(parentConf, param, {})
            _new = _parent.copy()
            for k, v in _current.items():
                if isinstance(v, maptype):
                    _new.setdefault(k, {})
                    _new[k].update(v)
                else:
                    _new[k] = v

            setattr(currentConf, param, _new)

        # startdir, subdirs - they are not merged
        mergedParams.update(('startdir', 'subdirs'))

        # project, features, cliopts - they are not merged and always use parent values
        for param in ('project', 'features', 'cliopts'):
            if parentConf is not None:
                setattr(currentConf, param, getattr(parentConf, param))
            mergedParams.add(param)

        # buildroot, realbuildroot - see _makeBuildDirParams
        mergedParams.update(('buildroot', 'realbuildroot'))

        # substvars, conditions, edeps
        for param in ('substvars', 'conditions', 'edeps'):
            mergeDict(param)
            mergedParams.add(param)

        # tasks - it's not merged
        mergedParams.add('tasks')

        # buildtypes, toolchains, platforms
        for param in ('buildtypes', 'toolchains', 'platforms'):
            mergeDict(param)
            mergedParams.add(param)

        # byfilter
        if parentConf:
            # append the parentConf.byfilter to the front of the currentConf.byfilter
            currentConf.byfilter[0:0] = parentConf.byfilter
        mergedParams.add('byfilter')

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

        filterBuildTypes = self._getFilterBuildtypes()
        buildtypes = list(filterBuildTypes.keys())
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
        for entry in self._conf.byfilter:
            cond = entry.get('for', {})
            try:
                _names = toList(cond.get('task', []))
            except AttributeError:
                _names = []
            names.extend(_names)
        for name in names:
            if DEPNAME_DELIMITER in name:
                msg = 'Name of task %r is invalid.' % name
                msg += ' Name can not contain symbol %r' % DEPNAME_DELIMITER
                raise ZenMakeConfError(msg, confpath = self.path)
        names = set(names)
        self._meta.tasknames = names

    def _handleFilterBuildtypes(self):
        destPlatform = PLATFORM
        filterBuildTypes = defaultdict(set)

        def handleCondition(entry, name):
            condition = entry.get(name, {})
            if isinstance(condition, stringtype):
                condition = entry[name] = {}

            buildtypes = toList(condition.get('buildtype', []))
            platforms = toListSimple(condition.get('platform', []))

            if buildtypes:
                if not platforms:
                    filterBuildTypes['all'].update(buildtypes)
                elif name == 'for' and destPlatform in platforms:
                    filterBuildTypes[destPlatform].update(buildtypes)
                elif name == 'not-for' and destPlatform not in platforms:
                    filterBuildTypes[destPlatform].update(buildtypes)

            return platforms

        for entry in self._conf.byfilter:

            enabledPlatforms = handleCondition(entry, 'for')
            disabledPlatforms = handleCondition(entry, 'not-for')

            defaultBuildType = entry.get('set', {}).get('default-buildtype', None)
            if defaultBuildType is not None:
                if not enabledPlatforms:
                    enabledPlatforms = KNOWN_PLATFORMS

                enabledPlatforms = set(enabledPlatforms) - set(disabledPlatforms)
                if destPlatform in enabledPlatforms:
                    filterBuildTypes['default'] = defaultBuildType

        self._meta.byfilter.buildtypes = filterBuildTypes

    def _getFilterBuildtypes(self):

        byfilter = self._meta.byfilter
        if 'buildtypes' not in byfilter:
            self._handleFilterBuildtypes()
            assert 'buildtypes' in byfilter

        return byfilter.buildtypes

    def _handleSupportedBuildTypes(self):
        """
        Calculate list of supported build types
        """

        destPlatform = PLATFORM

        supported = set()
        filterBuildTypes = self._getFilterBuildtypes()

        platformFound = False
        platforms = self._conf.platforms
        if destPlatform in platforms:
            platformFound = True
            supported = platforms[destPlatform].get('valid', [])
            supported = toListSimple(supported)
        else:
            supported = self._conf.buildtypes.keys()
        supported = set(supported)

        if destPlatform in filterBuildTypes:
            platformFound = True
            supported.update(filterBuildTypes[destPlatform])

        supported.update(filterBuildTypes.get('all', set()))

        if 'default' in supported:
            supported.remove('default')

        if platformFound and not supported:
            msg = "No valid build types for platform '%s'" % destPlatform
            raise ZenMakeConfError(msg, confpath = self.path)

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

        filterBuildTypes = self._getFilterBuildtypes()
        buildtype = filterBuildTypes.get('default', buildtype)

        supportedBuildTypes = self.supportedBuildTypes
        if buildtype is None:
            if len(supportedBuildTypes) == 1:
                buildtype = supportedBuildTypes[0]
            else:
                buildtype = ''

        if buildtype not in supportedBuildTypes:
            errmsg = "Default build type '%s'" % buildtype
            if 'default' in filterBuildTypes:
                errmsg += " from the config variable 'byfilter'"
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
            raise ZenMakeConfError(errmsg, confpath = self.path)

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

        # pylint: disable = protected-access

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
    def defaultLibVersion(self):
        """ Get default lib version """

        version = self._meta.get('default-lib-version')
        if version is not None:
            return version

        version = _RE_LIB_VER.findall(self.projectVersion)
        if version:
            version = '.'.join(version[0].split('.')[:3])
        else:
            version = ''

        self._meta['default-lib-version'] = version
        return version

    @property
    def cliopts(self):
        """ Get default options for cli from buildconf """
        return self._conf.cliopts

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
        default = buildtypes.get('default')
        if default is None:
            self._handleDefaultBuildType()
            assert 'default' in buildtypes
            default = buildtypes.default

        return default

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
    def conditions(self):
        """ Get conditions """

        conditions = self._meta.get('conditions')
        if conditions is not None:
            return conditions

        conditions = self._conf.conditions
        for condition in conditions.values():
            for param in condition:
                if param == 'env':
                    continue
                if param in ('platform', 'cpu-arch'):
                    _toList = toListSimple
                else:
                    _toList = toList
                condition[param] = _toList(condition[param])

        self._meta.conditions = conditions
        return conditions

    @property
    def edeps(self):
        """ Get edeps """

        return self._conf.edeps

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
            path = getNativePath(path)
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
        tasks = self._meta.tasks.get(buildtype)
        if tasks is not None:
            return tasks

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

        def getFilterCondition(entry, name):
            condition = entry.get(name, None)
            result = { 'condition' : condition }

            if condition is None:
                if name == 'for':
                    result['tasks'] = allTaskNames
                else: # if name == 'not-for'
                    assert name == 'not-for'
                    result['tasks'] = set()
                return result

            buildtypes = set(toList(condition.get('buildtype', [])))
            platforms = set(toListSimple(condition.get('platform', [])))
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

        for entry in self._conf.byfilter:

            enabled = getFilterCondition(entry, 'for')
            disabled = getFilterCondition(entry, 'not-for')

            if enabled['condition'] is None and disabled['condition'] is None:
                log.warn("WARN: buildconf.byfilter has an item without 'for' and 'not-for'. "
                         "It's probably a mistake.")

            enabledTasks = tuple(enabled['tasks'])
            disabledTasks = disabled['tasks']
            params = entry.get('set', {})

            for taskName in enabledTasks:
                if taskName in disabledTasks:
                    continue

                task = tasks[taskName]
                task.update(params)
                task.pop('default-buildtype', None)

        self._postprocessTaskParams(tasks)

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
        for name, info in srcToolchains.items():
            _vars = deepcopy(info) # don't change origin
            # checking of the 'kind' value is in 'configure' phase
            kind = _vars.pop('kind', None)

            for k, v in _vars.items():
                if k in TOOLCHAIN_PATH_ENVVARS:
                    # try to identify path and do warning if not
                    path = unfoldPath(self.startdir, v)
                    if not os.path.exists(path):
                        log.warn("Path to toolchain '%s' doesn't exist" % path)
                    v = path
                _vars[k] = toList(v)

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
        """
        buildroot - forced buildroot (from cmdline)
        """

        self._buildroot = buildroot
        self._orderedConfigs = []
        self._configs = {}
        self._virtConfigs = {}

        self.makeConfig(abspath(topdir))

    def makeConfig(self, dirpath, parent = None):
        """
        Make Config object for dirpath.
        """

        # It always must be an absolute norm path to avoid duplicates
        dirpath = abspath(dirpath)

        index = self._configs.get(dirpath)
        if index is not None:
            return self._orderedConfigs[index]

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

        bconf = Config(buildconf, self._buildroot, parent)
        self._orderedConfigs.append(bconf)
        startdir = bconf.startdir
        if startdir != dirpath:
            self._virtConfigs[startdir] = index

        for subdir in bconf.subdirs:
            if subdir in self._configs:
                # skip circular dependencies
                continue
            self.makeConfig(subdir, parent = bconf)

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

        return self._configs.get(dirpath, self._virtConfigs.get(dirpath, None))

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
