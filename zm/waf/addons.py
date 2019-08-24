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
from collections import namedtuple, defaultdict
from zm.utils import loadPyModule
from zm.error import ZenMakeLogicError

_cache = {}
_hooks = {}

WhenCall = namedtuple('WhenCall', 'pre, post')
HooksInfo = namedtuple('HooksInfo', 'order, funcs, conds')

def init():
    """ Module initialization """

    import zm.wscriptimpl as wscript

    def callHooks(hooksInfo, ctx):
        for name in hooksInfo.order:
            for func in hooksInfo.funcs.get(name, []):
                func(ctx)

    def wrap(method):
        def execute(ctx):
            methodName = method.__name__
            callHooks(_hooks[methodName].pre, ctx)
            method(ctx)
            callHooks(_hooks[methodName].post, ctx)
        return execute

    addonNames = allAddOnNames()
    addonNames.append('*') # for unknown modules
    for cmd in ('options', 'init', 'configure', 'build', 'shutdown'):
        _hooks[cmd] = WhenCall(
            pre  = HooksInfo( order = addonNames, funcs = defaultdict(list),
                              conds = {} ),
            post = HooksInfo( order = addonNames, funcs = defaultdict(list),
                              conds = {} )
        )
        setattr(wscript, cmd, wrap(getattr(wscript, cmd)))

def _arrangeHooksOrder(hooksInfo, condAddOns, addonName, before):
    if not condAddOns:
        return

    # Current a way to arrange order has one potential problem:
    # declaring each next pre/post hook method in addon with the same pre/post
    # condition and command can override previous changed order. It's not a
    # problem if only one such a hook function exists for each add-on or if
    # they don't change their order conditions.
    #TODO: remake algo
    addonNames = allAddOnNames()
    order = hooksInfo.order
    idxByFunc = order.index(addonName)
    for name in condAddOns:
        if name not in addonNames:
            name = '*' # for unknown modules
        idxCond = order.index(name)
        doSwap = any((
            before and idxCond < idxByFunc,
            not before and idxCond > idxByFunc
        ))

        if doSwap:
            order[idxByFunc], order[idxCond] = order[idxCond], order[idxByFunc]

def _checkHooksOrder(hooksInfo, addonName):

    order = hooksInfo.order
    idxCurrent = order.index(addonName)

    funcs = hooksInfo.funcs[addonName]
    for func in funcs:
        conds = hooksInfo.conds[func]
        beforeAddOns = conds['before']
        afterAddOns = conds['after']

        for addon in beforeAddOns:
            idxCond = order.index(addon)
            if idxCurrent > idxCond:
                raise ZenMakeLogicError("Invalid using of decorator precmd/postcmd")
        for addon in afterAddOns:
            idxCond = order.index(addon)
            if idxCurrent < idxCond:
                raise ZenMakeLogicError("Invalid using of decorator precmd/postcmd")

def _hookDecorator(func, hooksInfo, beforeAddOn, afterAddOn):

    addonNames = allAddOnNames()
    addonName = func.__module__.split('.')[-1][6:]

    if not beforeAddOn:
        beforeAddOn = []
    if not afterAddOn:
        afterAddOn = []

    if addonName not in addonNames:
        addonName = '*' # for unknown modules
    hooksInfo.funcs[addonName].append(func)
    hooksInfo.conds[func] = dict(
        before = beforeAddOn,
        after  = afterAddOn,
    )

    _arrangeHooksOrder(hooksInfo, beforeAddOn, addonName, True)
    _arrangeHooksOrder(hooksInfo, afterAddOn, addonName, False)
    _checkHooksOrder(hooksInfo, addonName)

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

    names = []
    for _, _, fnames in os.walk(os.path.dirname(os.path.abspath(__file__))):
        names = [ x for x in fnames if x.startswith('addon_') and x.endswith('.py') ]
        names = [ x[6:-3] for x in names ]
        break

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
