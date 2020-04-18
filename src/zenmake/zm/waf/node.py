# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import Node as WafNode
from waflib.Utils import is_win32 as _isWindows
from zm.utils import asmethod

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
