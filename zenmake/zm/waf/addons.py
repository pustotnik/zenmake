# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""
__all__ = [
    'precmd',
    'postcmd',
    'allAddOnNames',
    'loadAllAddOns',
    'getAddOn',
]

import os
from collections import namedtuple

from zm.pypkg import PkgPath
from zm.utils import loadPyModule

_cache = {}
_hooks = {}

WhenCall = namedtuple('WhenCall', 'pre, post')
HooksInfo = namedtuple('HooksInfo', 'funcs, sorted')

class FuncMeta(object):
    ''' Sortable func info for precmd/postcmd decorators '''

    __slots__ = ('beforeAddOn', 'afterAddOn', 'addon', 'func')

    def __init__(self, **kwargs):
        self.beforeAddOn = set(kwargs.get('beforeAddOn', []))
        self.afterAddOn = set(kwargs.get('afterAddOn', []))
        self.addon = kwargs.get('addon', None)
        self.func = kwargs.get('func', None)

    def __eq__(self, other):
        return self.func == other.func
    def __ne__(self, other):
        return not self.__eq__(other)
    def __lt__(self, other):
        return (other.addon in self.beforeAddOn) or \
               (self.addon in other.afterAddOn)
    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)
    def __gt__(self, other):
        return not self.__lt__(other)
    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

def init():
    """ Module initialization """

    import zm.wscriptimpl as wscript

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

    def wrap(method):
        def execute(ctx):
            methodName = method.__name__
            callHooks(_hooks[methodName].pre, ctx)
            method(ctx)
            callHooks(_hooks[methodName].post, ctx)
        return execute

    for cmd in ('options', 'init', 'configure', 'build', 'shutdown'):
        _hooks[cmd] = WhenCall(
            pre  = HooksInfo( funcs = [], sorted = set() ),
            post = HooksInfo( funcs = [], sorted = set() )
        )
        setattr(wscript, cmd, wrap(getattr(wscript, cmd)))

def _hookDecorator(func, hooksInfo, beforeAddOn, afterAddOn):

    # reset 'sorted' status
    hooksInfo.sorted.clear()

    addOnNames = set(allAddOnNames())
    moduleName = func.__module__.split('.')[-1]
    if not moduleName.startswith('addon_'):
        addonName = '*' # for unknown modules
    else:
        addonName = moduleName[6:]
        if addonName not in addOnNames:
            addonName = '*'

    condAddOns = [beforeAddOn, afterAddOn]
    for i in (0, 1):
        if not condAddOns[i]:
            condAddOns[i] = []
        if not isinstance(condAddOns[i], list):
            condAddOns[i] = [condAddOns[i]]
        for j, name in enumerate(condAddOns[i]):
            if name not in addOnNames:
                condAddOns[i][j] = '*'

    hooksInfo.funcs.append(FuncMeta(
        beforeAddOn = condAddOns[0],
        afterAddOn  = condAddOns[1],
        addon = addonName,
        func = func,
    ))

    return func

def precmd(cmdMethod, beforeAddOn = None, afterAddOn = None):
    """
    Decorator to declare add-on method to call 'pre' command method from wscript
    """
    def decorator(func):
        return _hookDecorator(func, _hooks[cmdMethod].pre,
                              beforeAddOn, afterAddOn)
    return decorator

def postcmd(cmdMethod, beforeAddOn = None, afterAddOn = None):
    """
    Decorator to declare add-on method to call 'post' command method from wscript
    """

    def decorator(func):
        return _hookDecorator(func, _hooks[cmdMethod].post,
                              beforeAddOn, afterAddOn)
    return decorator

def allAddOnNames():
    """ Return list of all existent add-ons here """

    if _cache:
        return _cache.keys()

    pkgPath = PkgPath(os.path.dirname(os.path.abspath(__file__)))
    fnames = pkgPath.files()
    names = [ x for x in fnames if x.startswith('addon_') and x.endswith('.py') ]
    names = [ x[6:-3] for x in names ]

    for name in names:
        _cache[name] = None
    return names

def loadAllAddOns():
    """ Load all existent add-ons here """

    addons = []
    addonNames = allAddOnNames()
    for name in addonNames:
        addons.append(getAddOn(name))
    return addons

def getAddOn(name):
    """ Get/Load add-on by name """
    names = allAddOnNames()
    if name not in names:
        raise NotImplementedError("Add-on %r is not implemented" % name)

    addon = _cache.get(name)
    if not addon:
        moduleName = 'zm.waf.addon_%s' % name
        addon = loadPyModule(moduleName, withImport = True)
        setup = getattr(addon, 'setup', None)
        if setup:
            setup()
        _cache[name] = addon

    return addon

init()
