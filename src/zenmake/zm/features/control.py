# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Core control stuff for supporting task features
"""

import os
from collections import namedtuple

from zm.constants import TASK_TARGET_KINDS, TASK_FEATURE_ALIESES
from zm.pyutils import stringtype, viewvalues
from zm.autodict import AutoDict as _AutoDict
from zm.pypkg import PkgPath
from zm.utils import loadPyModule, toList, getNativePath
from zm.error import ZenMakeError

# private cache
_cache = _AutoDict()

#######################################################################
## Base

MODULE_NAME_PREFIX = __name__[0:__name__.rfind('.') + 1]
CURRENT_MODULE_NAME = __name__[__name__.rfind('.') + 1:]

def _allModuleNames():
    """ Return list of all existent module names """

    names = _cache.get('module-names')
    if names:
        return names

    pkgPath = PkgPath(os.path.dirname(os.path.abspath(__file__)))
    fnames = pkgPath.files()
    names = [ x for x in fnames if x.endswith('.py') ]
    names = [ x[:-3] for x in names if x not in ('__init__', CURRENT_MODULE_NAME) ]

    _cache['module-names'] = names
    return names

def _getInitModules():

    modules = _cache.get('init-modules')
    if modules:
        return modules

    names = _allModuleNames()
    names = [ x for x in names if x.endswith('_init') ]

    modules = []
    for name in names:
        moduleName = MODULE_NAME_PREFIX + name
        modules.append(loadPyModule(moduleName, withImport = True))

    _cache['init-modules'] = modules
    return modules

def _generateFeaturesMap():

    modules = _getInitModules()

    targetMap = {}
    extensionsMap = {}
    aliesesMap = {}
    allFeatures = []

    for module in modules:
        spec = getattr(module, 'TASK_FEATURES_SETUP', {})
        for feature, params in spec.items():
            allFeatures.append(feature)
            if not params:
                continue

            targetKinds = params.get('target-kinds', [])
            for tkind in targetKinds:
                targetFeature = feature + tkind
                targetMap[targetFeature] = feature
                allFeatures.append(targetFeature)

            extensions = params.get('file-extensions', [])
            for ext in extensions:
                extensionsMap[ext] = feature

            alieses = params.get('alieses')
            if alieses:
                aliesesMap[feature] = alieses
                allFeatures.extend(alieses)

    return targetMap, extensionsMap, aliesesMap, frozenset(allFeatures)

def _generateToolchainVars():

    modules = _getInitModules()
    toolchainVars = {}
    for module in modules:
        spec = getattr(module, 'TOOLCHAIN_VARS', {})
        toolchainVars.update(spec)

    return toolchainVars

def _getFeatureDetectFuncs():
    modules = _getInitModules()
    funcs = []
    for module in modules:
        func = getattr(module, 'detectFeatures', None)
        if func:
            funcs.append(func)
    return funcs

TASK_TARGET_FEATURES_TO_LANG, \
FILE_EXTENSIONS_TO_LANG_FEATURE, \
TASK_LANG_FEATURES_TO_ALIESES, \
SUPPORTED_TASK_FEATURES = _generateFeaturesMap()

TASK_TARGET_FEATURES = frozenset(TASK_TARGET_FEATURES_TO_LANG.keys())
TASK_LANG_FEATURES = frozenset(TASK_TARGET_FEATURES_TO_LANG.values())

TOOLCHAIN_VARS = _generateToolchainVars()

# Could there be a more elegant solution to define these priorities?
TASK_LANG_FEATURES_PRIORITY = (
    'cxx', 'c', 'asm', 'fc', 'd'
)

def _gatherFileExtensions(src):
    """
    Returns the file extensions for the list of files given as input

    :param src: files to process
    :list src: list of string or waflib.Node.Node
    :return: set of file extensions
    :rtype: set of strings
	"""

    ret = set()
    for path in toList(src):
        if isinstance(path, stringtype):
            path = os.path.basename(getNativePath(path))
        else:
            # should be waflib.Node.Node
            path = path.name

        dotIndex = path.rfind('.')
        if dotIndex > 0: # if dotIndex == 0 it can mean something like '.ext'
            ret.add(path[dotIndex:])
    return ret

def resolveAliesesInFeatures(source, features):
    """
    Detect features from alieses in features
    """

    lfeatures = []

    alies = None
    for feature in features:
        if feature in TASK_FEATURE_ALIESES:
            alies = feature
            break
    else:
        # no alies
        return features

    # remove all alieses from features
    features = [ x for x in features if x not in TASK_FEATURE_ALIESES]

    extensions = _gatherFileExtensions(source)
    for ext in tuple(extensions):
        feature = FILE_EXTENSIONS_TO_LANG_FEATURE.get(ext)
        if feature:
            lfeatures.append(feature)

    if alies in TASK_TARGET_KINDS:
        _map = TASK_LANG_FEATURES_TO_ALIESES
        targetLangs = [ x for x in lfeatures if alies in _map.get(x, [])]

        if not targetLangs and not features:
            msg = 'Unable to determine how to resolve alies %r with features %r' % (alies, features)
            raise ZenMakeError(msg)

        # Only one target feature can be used for one build task
        targetFeature = None
        for lang in TASK_LANG_FEATURES_PRIORITY:
            if lang in targetLangs:
                targetFeature = lang + alies
                break
        else:
            if targetLangs:
                targetFeature = targetLangs[0] + alies

    features.extend(lfeatures)
    features.append(targetFeature)
    return features

#######################################################################
## Support for precmd/postcmd decorators

_hooks = {}

WhenCall = namedtuple('WhenCall', 'pre, post')
HooksInfo = namedtuple('HooksInfo', 'funcs, sorted')

class FuncMeta(object):
    ''' Sortable func info for precmd/postcmd decorators '''

    __slots__ = ('beforeModules', 'afterModules', 'module', 'func')

    def __init__(self, beforeModules, afterModules, module, func):
        self.beforeModules = set(beforeModules or [])
        self.afterModules = set(afterModules or [])
        self.module = module
        self.func = func

    def __eq__(self, other):
        return self.func == other.func
    def __ne__(self, other):
        return not self.__eq__(other)
    def __lt__(self, other):
        return (other.module in self.beforeModules) or \
               (self.module in other.afterModules)
    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)
    def __gt__(self, other):
        return not self.__lt__(other)
    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

def _initHooks():

    ready = _cache.get('hooks-are-ready')
    if ready:
        return

    import zm.waf.wscriptimpl as wscript

    def callHooks(hooksInfo, ctx):
        if not hooksInfo.sorted:
            hooksInfo.funcs.sort()
            # namedtuple is immutable for change atrribute instances:
            # we can change its value but cannot set it otherwise exception
            # 'AttributeError: can't set attribute' will be gotten.
            # So I emulate boolean value with 'set'.
            hooksInfo.sorted.add(1)
        for funcMeta in hooksInfo.funcs:
            funcMeta.func(ctx)

    def wrap(method, methodName):
        def execute(ctx):
            callHooks(_hooks[methodName].pre, ctx)
            method(ctx)
            callHooks(_hooks[methodName].post, ctx)
        return execute

    for cmd in ('options', 'init', 'configure', 'build', 'shutdown'):
        if not hasattr(wscript, cmd):
            continue
        _hooks[cmd] = WhenCall(
            pre  = HooksInfo( funcs = [], sorted = set() ),
            post = HooksInfo( funcs = [], sorted = set() )
        )
        setattr(wscript, cmd, wrap(getattr(wscript, cmd), cmd))

    _cache['hooks-are-ready'] = True

def _hookDecorator(func, hooksInfo, beforeModules, afterModules):

    # reset 'sorted' status
    hooksInfo.sorted.clear()

    moduleNames = set(_allModuleNames())
    moduleName = func.__module__.split('.')[-1]
    if moduleName not in moduleNames:
        moduleName = '*'

    condModules = [beforeModules, afterModules]
    for i in (0, 1):
        if not condModules[i]:
            condModules[i] = []
        if not isinstance(condModules[i], list):
            condModules[i] = [condModules[i]]
        for j, name in enumerate(condModules[i]):
            if name not in moduleNames:
                condModules[i][j] = '*'

    hooksInfo.funcs.append(FuncMeta(
        beforeModules = condModules[0],
        afterModules  = condModules[1],
        module = moduleName,
        func = func,
    ))

    return func

def precmd(cmdMethod, before = None, after = None):
    """
    Decorator to declare method to call 'pre' command method from wscript
    """
    def decorator(func):
        return _hookDecorator(func, _hooks[cmdMethod].pre, before, after)
    return decorator

def postcmd(cmdMethod, before = None, after = None):
    """
    Decorator to declare method to call 'post' command method from wscript
    """

    def decorator(func):
        return _hookDecorator(func, _hooks[cmdMethod].post, before, after)
    return decorator

#######################################################################
## Others

def loadFeatures(bconfManager):
    """
    Load modules for selected features. Not existing modules are ignored.
    """

    _initHooks()

    modules = _cache.setdefault('feature-modules', {})
    allModuleNames = set(_allModuleNames())

    detectFeaturesFuncs = _cache.get('detect-features-funcs')
    if not detectFeaturesFuncs:
        detectFeaturesFuncs = _getFeatureDetectFuncs()
        _cache['detect-features-funcs'] = detectFeaturesFuncs

    # gather unique features
    features = set()
    for bconf in bconfManager.configs:
        tasks = bconf.tasks
        for taskParams in viewvalues(tasks):
            features.update(taskParams['features'])
        for func in detectFeaturesFuncs:
            features.update(func(bconf))

    # ignore not existing modules
    features &= allModuleNames
    # remove already loaded
    features = features.difference(modules.keys())

    # load modules
    for feature in features:
        moduleName = MODULE_NAME_PREFIX + feature
        module = loadPyModule(moduleName, withImport = True)
        modules[feature] = module

def getLoadedFeatures():
    """
    Get names of loaded features
    """

    return _cache.get('feature-modules', {}).keys()

def loadTools(ctx, tools):
    """
    Load tool/toolchain from Waf or another places
    """

    # It's just a wrapper at present
    ctx.load(tools)

class ConfValidation(object):
    """
    Provides access to validation scheme specifics from features.
    """

    __slots__ = ()

    @staticmethod
    def getTaskSchemeSpecs():
        """ Get validation task scheme specifics """
        result = {}
        modules = _getInitModules()
        for module in modules:
            spec = getattr(module, 'VALIDATION_TASKSCHEME_SPEC', {})
            result.update(spec)
        return result

class ToolchainVars(object):
    """
    Class for getting some vars for supported toolchains
    """

    __slots__ = ()

    @staticmethod
    def allFlagVars():
        """
        For all toolchains return tuple of all env flag variables that have effect
        from system environment.
        """

        cacheName = 'all-env-flag-vars'
        _vars = _cache.get(cacheName)
        if _vars:
            return _vars

        _vars = []
        for info in TOOLCHAIN_VARS.values():
            _vars.extend(info['env-flagvars'])
        _vars = tuple(set(_vars))
        _cache[cacheName] = _vars
        return _vars

    @staticmethod
    def allCfgEnvVars():
        """
        For all toolchains return tuple of all WAF ConfigSet variables
        that is used on 'configure' step.
        """

        cacheName = 'all-cfg-env-vars'
        _vars = _cache.get(cacheName)
        if _vars:
            return _vars

        _vars = []
        for info in TOOLCHAIN_VARS.values():
            _vars.extend(info['cfgenv-vars'])
        _vars = tuple(set(_vars))
        _cache[cacheName] = _vars
        return _vars

    @staticmethod
    def allLangs():
        """
        Return tuple of all supported programming languages as lang features.
        """

        return tuple(TOOLCHAIN_VARS.keys())

    @staticmethod
    def varToSetToolchain(lang):
        """
        For selected language return environment variable to set toolchain.
        """

        if not lang or lang not in TOOLCHAIN_VARS:
            raise ZenMakeError("Toolchain for '%s' is not supported" % lang)
        return TOOLCHAIN_VARS[lang]['env-var']

    @staticmethod
    def allVarsToSetToolchain():
        """
        Return combined tuple of all environment variables to set toolchain.
        """

        cacheName = 'all-vars-to-set-toolchain'
        _vars = _cache.get(cacheName)
        if _vars:
            return _vars

        _vars = tuple([ x['env-var'] for x in TOOLCHAIN_VARS.values() ])
        _cache[cacheName] = _vars
        return _vars
