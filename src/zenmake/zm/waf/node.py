# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import re

from waflib import Node as WafNode
from waflib.Utils import is_win32 as _isWindows
from zm.pyutils import asmethod
from zm.utils import toListSimple
from zm import error

_antReCache = {}

@asmethod(WafNode, 'ant_matcher')
def _antMatcher(patterns, ignorecase):
    """
    Modified version of ant_matcher with fixed some bugs
    """

    reflags = re.I if ignorecase else 0
    results = []

    for pattern in toListSimple(patterns):
        pattern = pattern.replace('\\', '/').replace('//', '/')
        if pattern.endswith('/'):
            pattern += '**'

        accu = []
        prev = None
        for part in pattern.split('/'):
            if '**' in part:
                if len(part) != 2:
                    msg = 'Invalid part %r in pattern %r' % (part, pattern)
                    raise error.WafError(msg)
                if prev == '**':
                    # ignore repeated '**' parts
                    continue
                accu.append(part)
            else:
                cacheKey = (part, reflags)
                regExp = _antReCache.get(cacheKey)
                if regExp is None:
                    _part = part.replace('.', '[.]').replace('*', '.*')
                    _part = _part.replace('?', '.').replace('+', '\\+')
                    _part = '^%s$' % _part
                    try:
                        regExp = re.compile(_part, flags = reflags)
                    except Exception as ex:
                        msg = 'Invalid part %r in pattern %r' % (part, pattern)
                        raise error.WafError(msg, ex)
                    else:
                        _antReCache[cacheKey] = regExp
                accu.append(regExp)
            prev = part

        results.append(accu)
    return results

@asmethod(WafNode.Node, 'get_bld')
def _getBld(self):

    ctx = self.ctx
    srcNode = ctx.srcnode
    btypeNode = ctx.bldnode
    try:
        if ctx.buildWorkDirName:
            btypeNode = ctx.bldnode.parent
    except AttributeError:
        pass

    pathParts = []
    cur = self
    while cur.parent:
        if cur is btypeNode:
            return self
        if cur is srcNode:
            pathParts.reverse()
            return ctx.bldnode.make_node(pathParts)
        pathParts.append(cur.name)
        cur = cur.parent

    # the file is external to the current project, make a fake root in the current build directory
    pathParts.reverse()
    if _isWindows and pathParts and len(pathParts[0]) == 2 and pathParts[0].endswith(':'):
        pathParts[0] = pathParts[0][0]
    return ctx.bldnode.make_node(['__root__'] + pathParts)
