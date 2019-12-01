# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from waflib.Context import Context as WafContext
from waflib.ConfigSet import ConfigSet
from zm.constants import TASK_WAF_ALIESES, TASK_WAF_MAIN_FEATURES, TASK_FEATURES_LANGS
from zm.autodict import AutoDict as _AutoDict
from zm import utils, error
from zm.waf import wscriptimpl

joinpath = os.path.join

def ctxmethod(ctxClass, methodName = None, wrap = False):
    """
    Decorator to replace/attach method to existing Waf context class
    """

    def decorator(func):
        funcName = methodName if methodName else func.__name__
        if wrap:
            method = getattr(ctxClass, funcName)
            def execute(*args, **kwargs):
                method(*args, **kwargs)
                func(*args, **kwargs)
            setattr(ctxClass, funcName, execute)
        else:
            setattr(ctxClass, funcName, func)
        return func

    return decorator

# Context is the base class for all other context classes and it is not auto
# registering class. So it cannot be just declared for extending/changing.

# Valid task features for user in buildconf
WafContext.validUserTaskFeatures = TASK_WAF_MAIN_FEATURES | TASK_FEATURES_LANGS \
    | set(TASK_WAF_ALIESES)

@ctxmethod(WafContext, 'getbconf')
def _getCtxBuildConf(ctx):
    return ctx.bconfManager.config(ctx.path.abspath())

@ctxmethod(WafContext, 'zmcache')
def _getLocalCtxCache(ctx):
    #pylint: disable=protected-access
    try:
        return ctx._zmcache
    except AttributeError:
        pass

    ctx._zmcache = _AutoDict()
    return ctx._zmcache

@ctxmethod(WafContext, 'recurse')
def _contextRecurse(ctx, dirs, name = None, mandatory = True, once = True, encoding = None):
    #pylint: disable=too-many-arguments,unused-argument

    cache = ctx.zmcache().recurse

    for dirpath in utils.toList(dirs):
        if not os.path.isabs(dirpath):
            # absolute paths only
            dirpath = joinpath(ctx.path.abspath(), dirpath)

        dirpath = os.path.normpath(dirpath)
        bconf = ctx.bconfManager.config(dirpath)
        if not bconf:
            continue

        #node = ctx.root.find_node(bconf.path)
        node = ctx.root.make_node(joinpath(dirpath, 'virtual-buildconf'))
        funcName = name or ctx.fun

        tup = (node, funcName)
        if once and tup in cache:
            continue

        cache[tup] = True
        ctx.pre_recurse(node)

        try:
            # try to get function for command
            func = getattr(wscriptimpl, funcName, None)
            if not func:
                if not mandatory:
                    continue
                errmsg = 'No function %r defined in %s' % \
                            (funcName, wscriptimpl.__file__)
                raise error.ZenMakeError(errmsg)
            # call function for command
            func(ctx)
        finally:
            ctx.post_recurse(node)

@ctxmethod(WafContext, 'loadTasksFromFileCache')
def _loadTasksFromFileCache(ctx, cachefile):
    """
    Load cached tasks from config cache if it exists.
    """

    #pylint: disable = unused-argument

    key = 'zmtasks'

    result = {}
    try:
        env = ConfigSet()
        env.load(cachefile)
        if key in env:
            result = env[key]
    except EnvironmentError:
        pass

    return result
