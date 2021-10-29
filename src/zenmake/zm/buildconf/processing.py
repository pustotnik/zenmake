# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import re
import functools
from collections import defaultdict
from copy import deepcopy

from zm.constants import PLATFORM, KNOWN_PLATFORMS, DEPNAME_DELIMITER
from zm.constants import CWD, INVALID_BUILDTYPES, CONFTEST_DIR_PREFIX
from zm.autodict import AutoDict
from zm.error import ZenMakeError, ZenMakeConfError
from zm.pyutils import stringtype, maptype
from zm import utils, log
from zm.pathutils import unfoldPath, getNativePath, makePathsConf
from zm.buildconf import loader
from zm.buildconf.scheme import taskscheme, KNOWN_CONF_PARAM_NAMES, KNOWN_CONF_SUGAR_NAMES
from zm.buildconf.sugar import applySyntacticSugar
from zm.buildconf.paths import ConfPaths
from zm.buildconf.expression import Expression
from zm.buildconf.validator import Validator
from zm.features import ToolchainVars

joinpath = os.path.join
abspath  = os.path.abspath
normpath = os.path.normpath
dirname  = os.path.dirname
relpath  = os.path.relpath
isabs    = os.path.isabs
isdir    = os.path.isdir
osenv    = os.environ

toList        = utils.toList
toListSimple  = utils.toListSimple
substVars     = utils.substVars

_TOOLCHAIN_PATH_ENVVARS = frozenset(ToolchainVars.allSysVarsToSetToolchain())
_ALL_CONF_PARAM_NAMES = list(KNOWN_CONF_PARAM_NAMES | KNOWN_CONF_SUGAR_NAMES)
_CONF_PARAM_NAMES_FOR_BUILTIN = list(KNOWN_CONF_PARAM_NAMES - set([
    'startdir', 'buildroot', 'realbuildroot'
]))
_SET_KNOWN_PLATFORMS = set(KNOWN_PLATFORMS)

_RE_LIB_VER = re.compile(r"^\d+(?:\.\d+)*")
_TASKPARAMS_TOLIST_MAP = {}

_exprHandler = Expression()

#def _isDevVersion():
#    """
#    Detect if it is development version of the ZenMake
#    """
#    from zm import version
#    return version.isDev()

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
    Convert task param value to a list or to a dict (for 'source' only) with
    correct structure where it's necessary.
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

class _SubstVarsResolver(object):
    """
    Class to resolve substitution variables in a buildconf
    """

    __slots__ = '_bconf', '_cache', '_seen'

    def __init__(self, bconf):

        self._bconf = bconf
        self._cache = {}
        self._seen = set()

    def get(self, name):
        """
        Get value by the name.
        Returns None if not found
        """

        if name in self._cache:
            return self._cache[name]

        # pylint: disable = protected-access

        foundEnvVars = set()
        val = getattr(self._bconf._conf, name, None)
        if val is None:
            parentBConf = self._bconf.parent
            if parentBConf is not None:
                val = parentBConf._svarsResolver.get(name)

        if val:
            if not isinstance(val, stringtype):
                msg = 'The %r variable has invalid type to use as' % name
                msg += ' a substitution variable. Such a variable must be string.'
                raise ZenMakeConfError(msg, confpath = self._bconf.path)

            if id(val) in self._seen:
                msg = 'A circular dependency found in the variable %r' % name
                raise ZenMakeConfError(msg, confpath = self._bconf.path)

            self._seen.add(id(val))
            val = substVars(val, self.get, envVars = osenv, foundEnvVars = foundEnvVars)

        self._bconf._meta.envvars.update(foundEnvVars)
        self._cache[name] = val
        return val

class Config(object):
    """
    Class to get/process data from the certain buildconf module
    """

    # pylint: disable = too-many-public-methods

    __slots__ = '_conf', '_meta', '_confpaths', '_parent', '_svarsResolver'

    def __init__(self, buildconf, clivars = None, parent = None):
        """
        buildconf - module of a buildconf file
        clivars   - actual command line args/options like destdir, prefix, etc
        parent    - parent Config object
        """

        self._parent = parent
        self._conf = buildconf

        if clivars is None:
            clivars = parent._meta.clivars if parent else {}

        self._meta = AutoDict()
        self._meta.buildtypes.selected = None
        self._meta.envvars = set()
        self._meta.clivars = clivars

        self._meta.buildconffile = abspath(buildconf.__file__)
        self._meta.buildconfdir  = dirname(self._meta.buildconffile)

        self._svarsResolver = _SubstVarsResolver(self)
        self._substVarsInParams()

        # it must be done after substitutions
        self._makeStartDirParam()
        self._meta.rootdir = parent.rootdir if parent else self._meta.startdir

        # init/merge params including values from parent Config

        self._applyDefaults()
        self._applySugar()
        self._makeBuildDirParams(clivars.get('buildroot'))

        self._confpaths = ConfPaths(self)
        notHandled = self._handlePrimaryBuiltInVars()

        self._handleFilterBuildtypeNames()
        self._gatherCurrentBuildTypeNames()
        self._postValidateBuildtypeNames()
        self._applyBuildType()
        self._handleBuiltInVarsAfterBuildtype(notHandled)

        self._handleTaskNames() # must be called before merging
        self._merge()

    def _parentConf(self):
        # pylint: disable = protected-access
        return self._parent._conf if self._parent else None

    def _substVarsInParams(self):

        buildconf = self._conf
        foundEnvVars = set()
        svarGetter = self._svarsResolver.get

        def apply(param):
            if not param:
                return param

            if isinstance(param, stringtype):
                return substVars(param, svarGetter,
                                 envVars = osenv, foundEnvVars = foundEnvVars)

            if isinstance(param, (list, tuple)):
                return [apply(x) for x in param]
            if isinstance(param, maptype):
                return { k:apply(param[k]) for k in param }

            return param

        for name in _ALL_CONF_PARAM_NAMES:
            param = getattr(buildconf, name, None)
            if param:
                setattr(buildconf, name, apply(param))

        self._meta.envvars.update(foundEnvVars)

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

    def _postprocessTaskParams(self, tasks):

        # they are absolute paths
        rootdir = self.rootdir
        startdir = self.startdir

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

        if disabled:
            tasknames = set(self._meta.tasknames)
            for name in disabled:
                tasknames.remove(name)
                tasks.pop(name)
            self._meta.tasknames = tuple(tasknames)

    def _merge(self):

        mergedParams = set()
        currentConf = self._conf
        parentConf = self._parentConf()

        def mergeDictParam(currentConf, parentConf, param):
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

        # project, general, cliopts - they are not merged and always use parent values
        for param in ('project', 'general', 'cliopts'):
            if parentConf is not None:
                setattr(currentConf, param, getattr(parentConf, param))
            mergedParams.add(param)

        # buildroot, realbuildroot - see _makeBuildDirParams
        mergedParams.update(('buildroot', 'realbuildroot'))

        # conditions, edeps
        for param in ('conditions', 'edeps'):
            mergeDictParam(currentConf, parentConf, param)
            mergedParams.add(param)

        # tasks - it's not merged
        mergedParams.add('tasks')

        # buildtypes, toolchains
        for param in ('buildtypes', 'toolchains'):
            mergeDictParam(currentConf, parentConf, param)
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

    def _applySugar(self):

        applySyntacticSugar(self._conf)

    def _postValidateBuildtypeNames(self):

        # check buildtype names

        assert 'curnames' in self._meta.buildtypes
        buildtypes = self._meta.buildtypes.curnames
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
                msg = 'The %r name of a task is invalid.' % name
                msg += 'The name cannot contain symbol %r' % DEPNAME_DELIMITER
                raise ZenMakeConfError(msg, confpath = self.path)
        names = tuple(set(names))
        self._meta.tasknames = names

    def _handleFilterBuildtypeNames(self):
        destPlatform = PLATFORM
        filterBuildTypes = defaultdict(set)

        def handleCondition(entry, name):
            condition = entry.get(name, {})
            if isinstance(condition, stringtype) and condition == 'all':
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

        for entry in self._conf.byfilter:
            handleCondition(entry, 'for')
            handleCondition(entry, 'not-for')

        self._meta.byfilter.buildtypes = filterBuildTypes

    def _gatherCurrentBuildTypeNames(self):

        buildtypes = set(self._conf.buildtypes.keys())

        assert 'buildtypes' in self._meta.byfilter
        filterBuildTypes = self._meta.byfilter.buildtypes
        buildtypes.update(filterBuildTypes.get(PLATFORM, []))
        buildtypes.update(filterBuildTypes.get('all', []))

        if 'default' in buildtypes:
            buildtypes.remove('default')

        self._meta.buildtypes.curnames = buildtypes

    def _gatherAllBuildTypeNames(self):
        """
        Gather list of all build type names
        """

        metaBuildtypes = self._meta.buildtypes

        parent = self._parent
        if parent:
            buildtypes = set(metaBuildtypes.curnames)
            buildtypes.update(parent.supportedBuildTypes)
        else:
            buildtypes = metaBuildtypes.curnames

        if not buildtypes:
            # empty buildtype if others aren't detected
            buildtypes = set([''])

        metaBuildtypes.allnames = sorted(buildtypes)

    def _handleDefaultBuildType(self):
        """ Calculate default build type """

        buildtype = self._conf.buildtypes.get('default', None)
        if buildtype and not isinstance(buildtype, stringtype):
            buildtype = buildtype.get(PLATFORM,
                            buildtype.get('_', buildtype.get('no-match')))

        supportedBuildTypes = self.supportedBuildTypes
        if buildtype is None:
            if len(supportedBuildTypes) == 1:
                buildtype = supportedBuildTypes[0]
            else:
                buildtype = ''

        if buildtype not in supportedBuildTypes:
            errmsg = "Default build type '%s'" % buildtype
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

    def _applyFilterFor(self, buildtype, entry, allTaskNames, name):

        condition = entry.get(name)
        if isinstance(condition, stringtype) and condition == 'all':
            condition = entry[name] = {}
        result = { 'found' : condition is not None }

        if not condition:
            if name == 'for':
                result['tasks'] = allTaskNames
            else: # if name == 'not-for'
                result['tasks'] = []
            return result

        buildtypes = set(toList(condition.get('buildtype', [])))
        platforms = set(toListSimple(condition.get('platform', [])))
        tasks = set(toList(condition.get('task', [])))

        if not platforms:
            platforms = _SET_KNOWN_PLATFORMS
        if not buildtypes:
            buildtypes = self.supportedBuildTypes

        destPlatform = PLATFORM
        if destPlatform in platforms and buildtype in buildtypes:
            if not tasks:
                tasks = set(allTaskNames)
            tasks &= set(allTaskNames) # use tasks from current config only
            result['tasks'] = tuple(tasks)
        else:
            result['tasks'] = []

        return result

    def _applyFilterIf(self, buildtype, entry, taskNames):

        expr = entry.get('if')
        result = { 'found' : expr is not None, 'tasks': taskNames }

        if expr is None:
            return result

        if isinstance(expr, bool):
            result['tasks'] = taskNames if expr else []
            return result

        if expr.strip() == 'all':
            expr = entry['if'] = 'true'

        _expr = '[(%s) for task in tasks]' % expr

        def onExprError(exprWithErr, _, ex):
            msg = "There is syntax error in the expression: %r." % exprWithErr
            raise ZenMakeConfError(msg, confpath = self.path) from ex

        kwargs = {
            'attrs': {
                'buildtype' : buildtype,
                'platform' : PLATFORM,
                'tasks': taskNames,
            },
            'onError': functools.partial(onExprError, expr)
        }

        enabledTasks = _exprHandler.eval(_expr, **kwargs)
        enabledTasks = [taskNames[i] for i, x in enumerate(enabledTasks) if x]
        result['tasks'] = enabledTasks
        return result

    def _handleFilterTasks(self, buildtype, tasks):

        # make consistency of task params

        allTaskNames = self.taskNames
        for entry in self._conf.byfilter:

            conditionNotFound = True

            # for/not-for:
            enabled = self._applyFilterFor(buildtype, entry, allTaskNames, 'for')
            conditionNotFound = conditionNotFound and not enabled['found']

            disabled = self._applyFilterFor(buildtype, entry, allTaskNames, 'not-for')
            conditionNotFound = conditionNotFound and not disabled['found']

            enabledTasks = enabled['tasks']
            disabledTasks = disabled['tasks']
            if disabledTasks:
                enabledTasks = list(set(enabledTasks) - set(disabledTasks))

            # if:
            enabled = self._applyFilterIf(buildtype, entry, enabledTasks)
            conditionNotFound = conditionNotFound and not enabled['found']
            enabledTasks = enabled['tasks']

            if conditionNotFound:
                pad = " " * 6
                msg = "WARN: buildconf.byfilter has an item without "
                msg += "'for', 'not-for' and 'if' in:\n%s%r" % (pad, entry)
                msg += "\n%sIt's probably a mistake." % pad
                log.warn(msg)

            paramsSet = entry.get('set', {})
            for taskName in enabledTasks:
                task = tasks[taskName]
                task.update(paramsSet)

    def _handlePrimaryBuiltInVars(self):

        if self._parent:
            builtinvars = self._parent.builtInVars
        else:
            clivars = self._meta.clivars
            builtinvars = {}
            for name in ('destdir', 'prefix', 'bindir', 'libdir'):
                builtinvars[name] = clivars.get(name, '')

            builtinvars['prjname']      = self.projectName
            builtinvars['topdir']       = self.rootdir
            builtinvars['buildrootdir'] = self.confPaths.buildroot

        self._meta.builtinvars = builtinvars

        buildconf = self._conf

        apply = utils.substBuiltInVarsInParam
        splitListOfStrs = False
        notHandled = set()
        for name in _CONF_PARAM_NAMES_FOR_BUILTIN:
            param = getattr(buildconf, name, None)
            if param:
                setattr(buildconf, name, apply(param, builtinvars,
                                            splitListOfStrs, notHandled))
        return notHandled

    def _handleBuiltInVarsAfterBuildtype(self, notHandled):

        builtinvars = self._meta.builtinvars
        if not self._parent:
            builtinvars['buildtypedir'] = self.selectedBuildTypeDir

        if 'buildtypedir' not in notHandled:
            return

        # It definitely not the fastest way to handle 'buildtypedir' via
        # traversing all parameters in buildconf again but it just works and has
        # satisfactory performance at the moment.

        buildconf = self._conf
        apply = utils.substBuiltInVarsInParam
        splitListOfStrs = False
        for name in _CONF_PARAM_NAMES_FOR_BUILTIN:
            param = getattr(buildconf, name, None)
            if param:
                setattr(buildconf, name, apply(param, builtinvars, splitListOfStrs))

    def _applyBuildType(self):
        """
        Apply buildtype for the buildconf.
        """

        if self._meta.buildtypes.selected is not None:
            return

        parent = self._parent
        if parent:
            # pylint: disable = protected-access
            parent._applyBuildType()
            self._meta.buildtypes.selected = parent.selectedBuildType
            self._meta.buildtypedir = parent.selectedBuildTypeDir
            return

        buildtype = self._meta.clivars.get('buildtype')
        if buildtype is None:
            buildtype = self.defaultBuildType
        if not buildtype:
            buildtype = ''

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
        self._meta.buildtypedir = joinpath(self._confpaths.buildout, buildtype)

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
        Returns tuple of names.
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
    def usedEnvVars(self):
        """ Get list of used env vars in the buildconf """
        return self._meta.envvars

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

        return self._meta.buildtypes.selected

    @property
    def selectedBuildTypeDir(self):
        """ Get selected build type directory """

        return self._meta.buildtypedir

    @property
    def builtInVars(self):
        """ Get built-in vars """

        return self._meta.builtinvars

    @property
    def general(self):
        """ Get general features """
        return self._conf.general

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
        if 'allnames' not in buildtypes:
            self._gatherAllBuildTypeNames()
            assert 'allnames' in buildtypes

        return buildtypes.allnames

    @property
    def tasks(self):
        """
        Get all build tasks
        """

        buildtype = self.selectedBuildType
        tasks = self._meta.tasks.get(buildtype)
        if tasks is not None:
            return tasks

        tasks = {}

        for taskName in self.taskNames:

            task = tasks.setdefault(taskName, {})
            # 1. Copy existing params from origin task
            task.update(self._conf.tasks.get(taskName, {}))
            # 2. Copy/replace exising params of selected buildtype from 'buildtypes'
            task.update(self._conf.buildtypes.get(buildtype, {}))

        self._handleFilterTasks(buildtype, tasks)
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
                if k in _TOOLCHAIN_PATH_ENVVARS:
                    # try to identify path and do warning if not
                    path = unfoldPath(self.startdir, getNativePath(v))
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

    __slots__ = '_clivars', '_configs', '_virtConfigs', '_orderedConfigs'

    def __init__(self, topdir, clivars):
        """
        clivars - actual command line args/options like destdir, prefix, etc
        """

        self._clivars = clivars
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
        #if assist.isBuildConfChanged(buildconf, clivars) or _isDevVersion():
        #    loader.validate(buildconf)
        Validator(buildconf).run()

        index = len(self._orderedConfigs)
        self._configs[dirpath] = index

        bconf = Config(buildconf, self._clivars, parent)
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
