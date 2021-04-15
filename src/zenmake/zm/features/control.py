# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Core control stuff for supporting task features
"""

import os
from collections import namedtuple

from zm.autodict import AutoDict as _AutoDict
from zm.pypkg import PkgPath
from zm.utils import loadPyModule
from zm.error import ZenMakeError

# private cache
_cache = _AutoDict()

def _cached(cacheName):
    """ Decorator to use private cache """

    def decorator(method):
        def execute():
            _vars = _cache.get(cacheName)
            if _vars:
                return _vars
            _vars = method()
            _cache[cacheName] = _vars
            return _vars
        return execute

    return decorator

#######################################################################
## Base

MODULE_NAME_PREFIX = __name__[0:__name__.rfind('.') + 1]
CURRENT_MODULE_NAME = __name__[__name__.rfind('.') + 1:]

@_cached('module-names')
def _allModuleNames():
    """ Return list of all existent module names """

    pkgPath = PkgPath(os.path.dirname(os.path.abspath(__file__)))
    fnames = pkgPath.files()
    names = [ x[:-3] for x in fnames if x.endswith('.py') ]
    names = [ x for x in names if x not in ('__init__', CURRENT_MODULE_NAME) ]
    return names

@_cached('init-modules')
def _getInitModules():

    names = _allModuleNames()
    names = [ x for x in names if x.endswith('_init') ]

    modules = []
    for name in names:
        moduleName = MODULE_NAME_PREFIX + name
        modules.append(loadPyModule(moduleName, withImport = True))

    return modules

def _generateFeaturesMap():

    modules = _getInitModules()

    targetMap = {}
    extensionsMap = {}
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

    return targetMap, extensionsMap, frozenset(allFeatures)

def _generateToolchainVars():

    modules = _getInitModules()
    toolchainVars = {}
    for module in modules:
        spec = getattr(module, 'TOOLCHAIN_VARS', {})
        toolchainVars.update(spec)

    return toolchainVars

def _getBuildConfProcessingHooks():
    modules = _getInitModules()
    hooks = []
    for module in modules:
        func = getattr(module, 'getBuildConfTaskParamHooks', None)
        if func:
            hooks.extend(func())
    return tuple(hooks)

def _getFeatureDetectFuncs():
    modules = _getInitModules()
    funcs = []
    for module in modules:
        func = getattr(module, 'detectFeatures', None)
        if func:
            funcs.append(func)
    return funcs

def _generateToolchainVarToLang(toolchainVars):
    result = {}
    for lang, info in toolchainVars.items():
        var = info['sysenv-var']
        assert var not in result
        result[var] = lang

    return result

TASK_TARGET_FEATURES_TO_LANG, \
FILE_EXTENSIONS_TO_LANG, \
SUPPORTED_TASK_FEATURES = _generateFeaturesMap()

TASK_TARGET_FEATURES = frozenset(TASK_TARGET_FEATURES_TO_LANG.keys())
TASK_LANG_FEATURES = frozenset(TASK_TARGET_FEATURES_TO_LANG.values())

BUILDCONF_PREPARE_TASKPARAMS = _getBuildConfProcessingHooks()

TOOLCHAIN_VARS = _generateToolchainVars()
TOOLCHAIN_SYSVAR_TO_LANG = _generateToolchainVarToLang(TOOLCHAIN_VARS)

CCROOT_FEATURES = frozenset(
    ('c', 'cxx', 'asm', 'd', 'fc', 'java', 'cs', )
)

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
        return not self == other
    def __lt__(self, other):
        return (other.module in self.beforeModules) or \
               (self.module in other.afterModules)
    def __le__(self, other):
        return self == other or self < other
    def __gt__(self, other):
        return not self < other
    def __ge__(self, other):
        return self == other or self > other

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
        cmdFunc = getattr(wscript, cmd, None)
        if cmdFunc is None:
            continue
        _hooks[cmd] = WhenCall(
            pre  = HooksInfo( funcs = [], sorted = set() ),
            post = HooksInfo( funcs = [], sorted = set() )
        )
        setattr(wscript, cmd, wrap(cmdFunc, cmd))

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

    from zm import toolchains
    toolchains.reset()

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
        for taskParams in tasks.values():
            features.update(taskParams['features'])
        for func in detectFeaturesFuncs:
            features.update(func(bconf))

    # ignore not existing modules
    features &= allModuleNames
    # remove already loaded
    features = features.difference(modules.keys())

    if features & CCROOT_FEATURES:
        loadPyModule('zm.waf.ccroot', withImport = True)

    # load modules
    for feature in features:
        moduleName = MODULE_NAME_PREFIX + feature
        module = loadPyModule(moduleName, withImport = True)
        modules[feature] = module

    _cache['features-are-loaded'] = True

def getLoadedFeatures():
    """
    Get names of loaded features
    """

    return tuple(_cache.get('feature-modules', {}).keys())

def areFeaturesLoaded():
    """
    Return True if loadFeatures was called at least one time
    """

    return _cache.get('features-are-loaded', False)

class ConfValidation(object):
    """
    Provides access to validation scheme specifics from features.
    """

    __slots__ = ()

    @staticmethod
    def getTaskSchemeSpecs():
        """ Get validation task scheme specifics """
        result = {
            'base' : {},
            'export' : [],
            'select' : [],
        }
        modules = _getInitModules()
        for module in modules:
            spec = getattr(module, 'CONF_TASKSCHEME_SPEC', {})
            baseParams = spec.get('base', {})
            result['base'].update(baseParams)

            exportNames = spec.get('export', [])
            if isinstance(exportNames, bool):
                exportNames = baseParams.keys() if exportNames else []
            result['export'].extend(exportNames)

            selectNames = spec.get('select', [])
            if isinstance(selectNames, bool):
                selectNames = list(baseParams.keys()) if selectNames else []
                selectNames.extend(['export-%s' % x for x in exportNames])
            result['select'].extend(selectNames)

        return result

class ToolchainVars(object):
    """
    Class for getting some vars for supported toolchains
    """

    __slots__ = ()

    @staticmethod
    @_cached('all-sysenv-flagvars')
    def allSysFlagVars():
        """
        For all toolchains return tuple of all env flag variables that have effect
        from system environment.
        """

        _vars = []
        for info in TOOLCHAIN_VARS.values():
            _vars.extend(info['sysenv-flagvars'])
        return tuple(set(_vars))

    @staticmethod
    @_cached('all-cfgenv-flagvars')
    def allCfgFlagVars():
        """
        For all toolchains return tuple of all WAF ConfigSet flag variables
        that is used on 'configure' step.
        """

        _vars = []
        for info in TOOLCHAIN_VARS.values():
            _vars.extend(info['cfgenv-flagvars'])
        return tuple(set(_vars))

    @staticmethod
    def allLangs():
        """
        Return tuple of all supported programming languages as lang features.
        """

        return tuple(TOOLCHAIN_VARS.keys())

    @staticmethod
    def sysVarToSetToolchain(lang):
        """
        For selected language return environment variable to set toolchain.
        """

        if not lang or lang not in TOOLCHAIN_VARS:
            raise ZenMakeError("Toolchain for '%s' is not supported" % lang)
        return TOOLCHAIN_VARS[lang]['sysenv-var']

    @staticmethod
    def cfgVarToSetToolchain(lang):
        """
        For selected language return WAF ConfigSet variable to set/get toolchain.
        """

        if not lang or lang not in TOOLCHAIN_VARS:
            raise ZenMakeError("Toolchain for '%s' is not supported" % lang)
        return TOOLCHAIN_VARS[lang]['cfgenv-var']

    @staticmethod
    @_cached('all-sysvars-to-set-toolchain')
    def allSysVarsToSetToolchain():
        """
        Return combined tuple of all sys environment variables to set toolchain.
        """

        return tuple([ x['sysenv-var'] for x in TOOLCHAIN_VARS.values() ])

    @staticmethod
    @_cached('all-cfgvars-to-set-toolchain')
    def allCfgVarsToSetToolchain():
        """
        Return combined tuple of all WAF ConfigSet variables to set/get toolchain.
        """

        return tuple([ x['cfgenv-var'] for x in TOOLCHAIN_VARS.values() ])

    @staticmethod
    def langBySysVarToSetToolchain(var):
        """
        Return language of selected sys env var name.
        Examples: CC -> c, CXX -> cxx, DC -> d
        """

        return TOOLCHAIN_SYSVAR_TO_LANG.get(var)
