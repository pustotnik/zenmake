# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
from importlib import import_module as importModule

from waflib import Context as WafContextModule
from waflib.Context import Context as WafContext
from zm import ZENMAKE_DIR, WAF_DIR
from zm.autodict import AutoDict as _AutoDict
from zm import utils, error
from zm.waf import wscriptimpl

joinpath = os.path.join
normpath = os.path.normpath
isabspath = os.path.isabs

DEFAULT_TOOLDIRS = [
    joinpath(ZENMAKE_DIR, 'zm', 'tools'),
    joinpath(ZENMAKE_DIR, 'waf', 'waflib', 'Tools'),
    joinpath(ZENMAKE_DIR, 'waf', 'waflib', 'extras'),
]

def ctxmethod(ctxClass, methodName = None, wrap = False, callOrigFirst = True):
    """
    Decorator to replace/attach method to existing Waf context class
    """

    def decorator(func):
        funcName = methodName if methodName else func.__name__
        if wrap:
            origMethod = getattr(ctxClass, funcName)

            if callOrigFirst:
                def execute(*args, **kwargs):
                    origMethod(*args, **kwargs)
                    func(*args, **kwargs)
            else:
                def execute(*args, **kwargs):
                    func(*args, **kwargs)
                    origMethod(*args, **kwargs)

            setattr(ctxClass, funcName, execute)
        else:
            setattr(ctxClass, funcName, func)
        return func

    return decorator

# Context is the base class for all other context classes and it is not auto
# registering class. So it cannot be just declared for extending/changing.

@ctxmethod(WafContext, '__init__', wrap = True, callOrigFirst = False)
def _ctxInit(self, **kwargs):
    self.bconfManager = kwargs.get('bconfManager')

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
        if not isabspath(dirpath):
            # absolute paths only
            dirpath = joinpath(ctx.path.abspath(), dirpath)

        dirpath = normpath(dirpath)
        bconf = ctx.bconfManager.config(dirpath)
        if not bconf:
            continue

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

@ctxmethod(WafContext, 'getPathNode')
def _getPathNode(self, path):

    cache = self.zmcache().ctxpath
    node = cache.get(path)
    if node is not None:
        return node

    node = self.root.make_node(path)
    cache[path] = node
    return node

@ctxmethod(WafContext, 'getStartDirNode')
def _getStartDirNode(self, startdir):

    cache = self.zmcache().startdirpath
    node = cache.get(startdir)
    if node is not None:
        return node

    rootdir = self.bconfManager.root.rootdir
    path = normpath(joinpath(rootdir, startdir))
    node = self.root.make_node(path)
    cache[path] = node
    return node

def loadTool(tool, tooldirs = None, withSysPath = True):
    """
    Alternative version of WafContextModule.load_tool
    """

    if tool == 'java':
        tool = 'javaw'
    else:
        tool = tool.replace('++', 'xx')

    oldSysPath = sys.path

    if not withSysPath:
        sys.path = []
        if not tooldirs:
            sys.path = [WAF_DIR]

    if not tooldirs:
        tooldirs = DEFAULT_TOOLDIRS
    sys.path = tooldirs + sys.path

    module = None
    try:
        module = importModule(tool)
        WafContext.tools[tool] = module
    except ImportError as ex:
        toolsSysPath = list(sys.path)
        ex.toolsSysPath = toolsSysPath
        # for Waf
        ex.waf_sys_path = toolsSysPath
        raise
    finally:
        sys.path = oldSysPath

    return module

def _wafLoadTool(tool, tooldir = None, ctx = None, with_sys_path = True):
    # pylint: disable = invalid-name, unused-argument
    return loadTool(tool, tooldir, with_sys_path)

WafContextModule.load_tool = _wafLoadTool

@ctxmethod(WafContext, 'loadTool')
def _loadToolWitFunc(ctx, tool, tooldirs = None, callFunc = None, withSysPath = True):

    module = loadTool(tool, tooldirs, withSysPath)
    func = getattr(module, callFunc or ctx.fun, None)
    if func:
        func(ctx)

    return module

@ctxmethod(WafContext, 'load')
def _loadTools(ctx, tools, *args, **kwargs):
    """ This function is for compatibility with Waf """

    # pylint: disable = unused-argument

    tools = utils.toList(tools)
    tooldirs = utils.toList(kwargs.get('tooldir', ''))
    withSysPath = kwargs.get('with_sys_path', True)
    callFunc = kwargs.get('name', None)

    for tool in tools:
        _loadToolWitFunc(ctx, tool, tooldirs, callFunc, withSysPath)
