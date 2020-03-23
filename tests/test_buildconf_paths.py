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
from zm.autodict import AutoDict
from zm.buildconf.paths import ConfPaths
from zm.constants import *

joinpath = os.path.join

def testAll(testingBuildConf):

    dirname    = os.path.dirname
    abspath    = os.path.abspath
    unfoldPath = utils.unfoldPath

    fakeBuildConf = testingBuildConf
    fakeBuildConf.startdir = '.'
    fakeBuildConf.realbuildroot = 'realbuildroot'

    bconf = AutoDict(
        _conf = asRealConf(fakeBuildConf),
        path = abspath(fakeBuildConf.__file__),
        confdir = dirname(abspath(fakeBuildConf.__file__)),
    )

    bcpaths = ConfPaths(bconf)

    assert bcpaths.buildconffile == abspath(fakeBuildConf.__file__)
    assert bcpaths.buildconfdir  == dirname(bcpaths.buildconffile)
    assert bcpaths.startdir      == fakeBuildConf.startdir
    assert bcpaths.buildroot     == fakeBuildConf.buildroot
    assert bcpaths.realbuildroot == fakeBuildConf.realbuildroot
    assert bcpaths.buildout      == joinpath(bcpaths.buildroot, BUILDOUTNAME)
    assert bcpaths.wscripttop    == fakeBuildConf.startdir
    assert bcpaths.wscriptout    == bcpaths.buildout
    assert bcpaths.wafcachedir   == joinpath(bcpaths.buildout, WAF_CACHE_DIRNAME)
    assert bcpaths.wafcachefile  == joinpath(bcpaths.wafcachedir, WAF_CACHE_NAMESUFFIX)
    assert bcpaths.zmcachedir    == bcpaths.wafcachedir
    assert bcpaths.zmmetafile  == joinpath(bcpaths.buildroot, ZENMAKE_BUILDMETA_FILENAME)
