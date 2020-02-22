# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys

from waflib import Utils
from waflib.TaskGen import after_method, feature
# pylint: disable = unused-import
from waflib.Tools import ccroot # don't remove
# pylint: enable = unused-import

from zm.utils import toList, uniqueListWithOrder

# waflib.Tools.ccroot must be always imported
assert 'waflib.Tools.ccroot' in sys.modules

@feature('c', 'cxx', 'd', 'fc', 'javac', 'cs', 'uselib', 'asm')
@after_method('process_use')
def propagate_uselib_vars(self):
    """
    Alternative version of propagate_uselib_vars from waflib.Tools.ccroot
    The main reason is to change order of flag vars
    """

    # pylint: disable = invalid-name

    useLibVars = self.get_uselib_vars()
    env = self.env

    useLibFeatures = self.features + toList(getattr(self, 'uselib', []))
    for var in useLibVars:
        vals = []
        val = getattr(self, var.lower(), [])
        if val:
            vals += toList(val)

        for _feature in useLibFeatures:
            val = env['%s_%s' % (var, _feature)]
            if val:
                vals += val

        if vals:
            vals += env[var]
            # remove duplicates: keep only last unique values in the list
            vals = uniqueListWithOrder(reversed(vals))
            vals.reverse()
            env[var] = vals

#TODO: remove it when this patch appears in the Waf
# See https://gitlab.com/ita1024/waf/issues/2272
if Utils.is_win32:
    @feature('c', 'cxx', 'd', 'asm', 'fc', 'includes')
    @after_method('propagate_uselib_vars', 'process_source')
    def apply_incpaths(self):
        # pylint: disable = invalid-name, missing-docstring
        lst = self.to_incnodes(toList(getattr(self, 'includes', [])) + self.env.INCLUDES)
        self.includes_nodes = lst
        cwd = self.get_cwd()
        self.env.INCPATHS = [x.path_from(cwd) if x.is_child_of(self.bld.srcnode) \
                             else x.abspath() for x in lst]
