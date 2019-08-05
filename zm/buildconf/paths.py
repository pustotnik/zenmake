# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 There are functions and classes specific to process with our wscript.
"""

import os
from zm import utils
from zm.constants import WAF_CACHE_DIRNAME, WAF_CACHE_NAMESUFFIX, \
                         ZENMAKE_COMMON_FILENAME, \
                         BUILDOUTNAME, WSCRIPT_NAME

joinpath = os.path.join

class BuildConfPaths(object):
    """
    Class to calculate different paths depending on buildconf
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, conf):
        dirname    = os.path.dirname
        abspath    = os.path.abspath
        unfoldPath = utils.unfoldPath

        self.buildconffile = abspath(conf.__file__)
        self.buildconfdir  = dirname(self.buildconffile)
        self.buildroot     = unfoldPath(self.buildconfdir, conf.buildroot)
        self.buildsymlink  = unfoldPath(self.buildconfdir, conf.buildsymlink)
        self.buildout      = joinpath(self.buildroot, BUILDOUTNAME)
        self.projectroot   = unfoldPath(self.buildconfdir, conf.project['root'])
        self.srcroot       = unfoldPath(self.buildconfdir, conf.srcroot)

        # TODO: add as option
        #self.wscripttop    = self.buildroot
        self.wscripttop    = self.projectroot

        self.wscriptout    = self.buildout
        self.wscriptfile   = joinpath(self.wscripttop, WSCRIPT_NAME)
        self.wscriptdir    = dirname(self.wscriptfile)
        self.wafcachedir   = joinpath(self.buildout, WAF_CACHE_DIRNAME)
        self.wafcachefile  = joinpath(self.wafcachedir, WAF_CACHE_NAMESUFFIX)
        self.zmcachedir    = self.wafcachedir
        self.zmcmnfile     = joinpath(self.buildout, ZENMAKE_COMMON_FILENAME)

    def __eq__(self, other):
        return vars(self) == vars(other)