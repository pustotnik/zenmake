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
from zm import error
from zm.utils import toList, asmethod
from zm.waf.assist import loadZenMakeMetaFile
from zm.waf import wscriptimpl

joinpath = os.path.join
normpath = os.path.normpath
isabspath = os.path.isabs

DEFAULT_TOOLDIRS = [
    joinpath(ZENMAKE_DIR, 'zm', 'tools'),
    joinpath(ZENMAKE_DIR, 'waf', 'waflib', 'Tools'),
    joinpath(ZENMAKE_DIR, 'waf', 'waflib', 'extras'),
]

# Context is the base class for all other context classes and it is not auto
# registering class. So it cannot be just declared for extending/changing.

_cache = {}

@asmethod(WafContext, '__init__', wrap = True, callOrigFirst = False)
def _ctxInit(self, **kwargs):
    self.bconfManager = kwargs.get('bconfManager')

@asmethod(WafContext, 'zmMetaConf')
def _getZmMetaConf(self):
    if 'zm-meta-conf' in _cache:
        return _cache['zm-meta-conf']

    bconfPaths = self.bconfManager.root.confPaths
    _cache['zm-meta-conf'] = data = loadZenMakeMetaFile(bconfPaths.zmmetafile)
    return data

@asmethod(WafContext, 'getbconf')
def _getBuildConf(self):
    return self.bconfManager.config(self.path.abspath())

@asmethod(WafContext, 'zmcache')
def _getLocalCache(self):
    #pylint: disable=protected-access
    try:
        return self._zmcache
    except AttributeError:
        pass

    self._zmcache = _AutoDict()
    return self._zmcache

@asmethod(WafContext, 'recurse')
def _ctxRecurse(self, dirs, name = None, mandatory = True, once = True, encoding = None):
    #pylint: disable=too-many-arguments,unused-argument

    cache = self.zmcache().recurse

    for dirpath in toList(dirs):
        if not isabspath(dirpath):
            # absolute paths only
            dirpath = joinpath(self.path.abspath(), dirpath)

        dirpath = normpath(dirpath)
        bconf = self.bconfManager.config(dirpath)
        if not bconf:
            continue

        node = self.root.make_node(joinpath(dirpath, 'virtual-buildconf'))
        funcName = name or self.fun

        tup = (node, funcName)
        if once and tup in cache:
            continue

        cache[tup] = True
        self.pre_recurse(node)

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
            func(self)
        finally:
            self.post_recurse(node)

@asmethod(WafContext, 'getPathNode')
def _getPathNode(self, path):

    cache = self.zmcache().ctxpath
    node = cache.get(path)
    if node is not None:
        return node

    node = self.root.make_node(path)
    cache[path] = node
    return node

@asmethod(WafContext, 'getStartDirNode')
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

@asmethod(WafContext, 'loadTool')
def _loadToolWitFunc(self, tool, tooldirs = None, callFunc = None, withSysPath = True):

    module = loadTool(tool, tooldirs, withSysPath)
    func = getattr(module, callFunc or self.fun, None)
    if func:
        func(self)

    return module

@asmethod(WafContext, 'load')
def _loadTools(self, tools, *args, **kwargs):
    """ This function is for compatibility with Waf """

    # pylint: disable = unused-argument

    tools = toList(tools)
    tooldirs = toList(kwargs.get('tooldir', ''))
    withSysPath = kwargs.get('with_sys_path', True)
    callFunc = kwargs.get('name', None)

    for tool in tools:
        _loadToolWitFunc(self, tool, tooldirs, callFunc, withSysPath)
