# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import pytest
from tests.common import asRealConf
from zm import utils
from zm.buildconf.paths import BuildConfPaths
from zm.constants import *

joinpath = os.path.join

def testAll(testingBuildConf):
    fakeBuildConf = testingBuildConf
    bcpaths = BuildConfPaths(asRealConf(fakeBuildConf))

    dirname    = os.path.dirname
    abspath    = os.path.abspath
    unfoldPath = utils.unfoldPath

    assert bcpaths.buildconffile == abspath(fakeBuildConf.__file__)
    assert bcpaths.buildconfdir  == dirname(bcpaths.buildconffile)
    assert bcpaths.buildroot     == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.buildroot)
    assert bcpaths.realbuildroot == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.realbuildroot)
    assert bcpaths.buildout      == joinpath(bcpaths.buildroot, BUILDOUTNAME)
    assert bcpaths.projectroot   == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.project['root'])
    assert bcpaths.srcroot       == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.srcroot)
    assert bcpaths.wscriptout    == bcpaths.buildout
    assert bcpaths.wscriptfile   == joinpath(bcpaths.wscripttop, WSCRIPT_NAME)
    assert bcpaths.wscriptdir    == dirname(bcpaths.wscriptfile)
    assert bcpaths.wafcachedir   == joinpath(bcpaths.buildout,
                                                WAF_CACHE_DIRNAME)
    assert bcpaths.wafcachefile  == joinpath(bcpaths.wafcachedir,
                                                WAF_CACHE_NAMESUFFIX)
    assert bcpaths.zmcachedir    == bcpaths.wafcachedir
    assert bcpaths.zmcmnfile     == joinpath(bcpaths.buildout,
                                                ZENMAKE_COMMON_FILENAME)
    assert bcpaths.wscripttop == bcpaths.projectroot or \
            bcpaths.wscripttop == bcpaths.buildroot
