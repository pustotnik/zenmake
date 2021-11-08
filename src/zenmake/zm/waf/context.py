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
from zm import error, log
from zm.pyutils import asmethod
from zm.utils import toList
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

DEFAULT_STDOUT_MSG_LEN = 40
MAX_STDOUT_MSG_LEN = 100
STDOUT_MSG_LEN_STEP = 5

_MSG_LOG_SEPARATOR = MAX_STDOUT_MSG_LEN * '-'

# Context is the base class for all other context classes and it is not auto
# registering class. So it cannot be just declared for extending/changing.

_cache = {}

@asmethod(WafContext, '__init__', wrap = True, callOrigFirst = False)
def _ctxInit(self, **kwargs):
    self.zmcache = _AutoDict()
    self.bconfManager = kwargs.get('bconfManager')

@asmethod(WafContext, 'zmMetaConf')
def _getZmMetaConf(self):
    if 'zm-meta-conf' in _cache:
        return _cache['zm-meta-conf']

    bconfPaths = self.bconfManager.root.confPaths
    _cache['zm-meta-conf'] = data = loadZenMakeMetaFile(bconfPaths.zmmetafile)
    return data

@asmethod(WafContext, 'getbconf')
def _getBuildConf(self, pathNode):
    return self.bconfManager.config(pathNode.abspath())

@asmethod(WafContext, 'recurse')
def _ctxRecurse(self, dirs, name = None, mandatory = True, once = True, encoding = None):
    #pylint: disable=too-many-arguments,unused-argument

    cache = self.zmcache.recurse

    for dirpath in toList(dirs):
        if not isabspath(dirpath):
            # absolute paths only
            dirpath = joinpath(self.path.abspath(), dirpath)

        dirpath = normpath(dirpath)
        bconf = self.bconfManager.config(dirpath)
        if not bconf:
            continue

        node = self.root.make_node(dirpath)
        funcName = name or self.fun

        tup = (node, funcName)
        if once and tup in cache:
            continue

        cache[tup] = True
        self.stack_path.append(self.path)
        self.path = node

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
            self.path = self.stack_path.pop()

@asmethod(WafContext, 'getPathNode')
def _getPathNode(self, path):

    cache = self.zmcache.pathnodes
    node = cache.get(path)
    if node is not None:
        return node

    node = self.root.make_node(path)
    cache[path] = node
    return node

@asmethod(WafContext, 'getStartDirNode')
def _getStartDirNode(self, startdir):

    cache = self.zmcache.pathnodes
    node = cache.get(startdir)
    if node is not None:
        return node

    rootdir = self.bconfManager.root.rootdir
    fullpath = normpath(joinpath(rootdir, startdir))
    node = self.root.make_node(fullpath)
    cache[startdir] = cache[fullpath] = node
    return node

@asmethod(WafContext, 'startMsg')
def _startMsg(self, *args, **kwargs):

    if kwargs.get('quiet'):
        return

    msg = kwargs.get('msg') or args[0]

    try:
        if self.in_msg:
            self.in_msg += 1
            return
    except AttributeError:
        self.in_msg = 0
    self.in_msg += 1

    try:
        lineWidth = self.lineWidth
    except AttributeError:
        lineWidth = DEFAULT_STDOUT_MSG_LEN

    msgLen = len(msg)
    if msgLen > lineWidth:
        div, mod = divmod(msgLen, STDOUT_MSG_LEN_STEP)
        lineWidth = STDOUT_MSG_LEN_STEP * div + (STDOUT_MSG_LEN_STEP if mod > 0 else 0)
    self.lineWidth = lineWidth = min(lineWidth, MAX_STDOUT_MSG_LEN)

    self.to_log(_MSG_LOG_SEPARATOR)
    self.to_log(msg)

    if msgLen > lineWidth:
        msg = '%s%s' % (msg[0 : lineWidth - 3], '...')
    log.pprint('NORMAL', '%s :' % msg.ljust(lineWidth), sep = '')

WafContext.start_msg = _startMsg

@asmethod(WafContext, 'endMsg')
def _endMsg(self, *args, **kwargs):

    if kwargs.get('quiet'):
        return

    self.in_msg -= 1
    if self.in_msg:
        return

    result = kwargs.get('result') or args[0]

    defaultColor = 'GREEN'
    if result is True:
        msg = 'ok'
    elif not result:
        msg = 'not found'
        defaultColor = 'YELLOW'
    else:
        msg = str(result)

    postfix = kwargs.get('endmsg-postfix')
    if postfix is not None:
        msg += postfix

    self.to_log(msg)
    color = kwargs.get('color')
    if color is None:
        if len(args) > 1 and args[1] in log.colorSettings:
            color = args[1]
        else:
            color = defaultColor

    log.pprint(color, msg)

WafContext.end_msg = _endMsg

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
