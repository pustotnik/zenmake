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
from zm.buildconf.paths import ConfPaths
from zm.constants import *

joinpath = os.path.join

@pytest.fixture(params = [None, 'somedir'])
def buildroot(request):
    return request.param

@pytest.fixture(params = [None, 'somedir2'])
def realbuildroot(request):
    return request.param

def testAll(buildroot, realbuildroot, monkeypatch, testingBuildConf):

    dirname    = os.path.dirname
    abspath    = os.path.abspath
    unfoldPath = utils.unfoldPath

    fakeBuildConf = testingBuildConf

    if not buildroot:
        buildroot = fakeBuildConf.buildroot

    if realbuildroot:
        monkeypatch.setattr(fakeBuildConf, 'realbuildroot', realbuildroot)

    bcpaths = ConfPaths(asRealConf(fakeBuildConf), buildroot)

    assert bcpaths.buildconffile == abspath(fakeBuildConf.__file__)
    assert bcpaths.buildconfdir  == dirname(bcpaths.buildconffile)
    assert bcpaths.buildroot     == unfoldPath(bcpaths.buildconfdir,
                                                buildroot)
    if realbuildroot:
        assert bcpaths.realbuildroot == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.realbuildroot)
    else:
        assert bcpaths.realbuildroot == bcpaths.buildroot

    assert bcpaths.buildout      == joinpath(bcpaths.buildroot, BUILDOUTNAME)
    assert bcpaths.projectroot   == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.project['root'])
    assert bcpaths.srcroot       == unfoldPath(bcpaths.buildconfdir,
                                                fakeBuildConf.srcroot)
    assert bcpaths.wscriptout    == bcpaths.buildout
    assert bcpaths.wafcachedir   == joinpath(bcpaths.buildout,
                                                WAF_CACHE_DIRNAME)
    assert bcpaths.wafcachefile  == joinpath(bcpaths.wafcachedir,
                                                WAF_CACHE_NAMESUFFIX)
    assert bcpaths.zmcachedir    == bcpaths.wafcachedir
    assert bcpaths.zmcmnconfset  == joinpath(bcpaths.buildroot,
                                                ZENMAKE_CMN_CFGSET_FILENAME)
    assert bcpaths.wscripttop == bcpaths.projectroot or \
            bcpaths.wscripttop == bcpaths.buildroot
