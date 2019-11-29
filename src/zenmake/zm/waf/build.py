# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from waflib.Build import BuildContext as WafBuildContext
from zm import log
from zm.waf.context import ctxmethod

class BuildContext(WafBuildContext):
    """ Context for command 'build' """

    # No methods here at present. See below.

# WafBuildContext is used for many other waf commands as the base class
# and so to insert new methods into this class the decorator @ctxmethod is used.

@ctxmethod(WafBuildContext, 'validateVariant')
def _validateVariant(self):
    """ Check current variant and return it """

    if self.variant is None:
        self.fatal('No variant!')

    buildtype = self.variant
    if buildtype not in self.env.zmtasks['all']:
        if self.cmd == 'clean':
            log.info("Buildtype '%s' not found. Nothing to clean" % buildtype)
            return None
        self.fatal("Buildtype '%s' not found! Was step 'configure' missed?"
                   % buildtype)
    return buildtype

@ctxmethod(WafBuildContext, 'getTasks')
def _getTasks(self, buildtype):

    zmtasks = self.env.zmtasks
    return zmtasks['all'][buildtype]

@ctxmethod(WafBuildContext, 'getTaskPathNode')
def _getTaskPathNode(self, taskStartDir):

    cache = self.zmcache().bldpath
    if taskStartDir in cache:
        return cache[taskStartDir]

    bconf = self.getbconf()
    taskPath = os.path.abspath(os.path.join(bconf.rootdir, taskStartDir))
    pathNode = self.root.make_node(taskPath)

    cache[taskStartDir] = pathNode
    return pathNode
