# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import shutil
import pytest
from zm.error import *
import tests.common as cmn
from zm.constants import DEFAULT_BUILDROOTNAME
from zm.buildconf.validator import Validator
from zm.buildconf import loader as bconfloader

file = __file__

class FakeBuildConf:
    __name__ = 'testconf'
    __file__ = file

def validateConf(buildconf):
    Validator(buildconf).run(checksOnly = True, doAsserts = True)

def checkCommonDefaults(buildconf):

    assert not hasattr(buildconf, 'startdir')
    assert not hasattr(buildconf, 'realbuildroot')

    assert hasattr(buildconf, 'cliopts')
    assert buildconf.cliopts == {}

    assert hasattr(buildconf, 'general')

    assert hasattr(buildconf, 'subdirs')
    assert buildconf.subdirs == []

    assert hasattr(buildconf, 'project')

    for param in ('toolchains', 'buildtypes', 'tasks'):
        assert hasattr(buildconf, param)
        assert getattr(buildconf, param) == {}

    assert hasattr(buildconf, 'byfilter')
    assert buildconf.byfilter == []

def testInitDefaults():

    ######### top-level

    buildconf = FakeBuildConf()
    projectDir = os.path.dirname(buildconf.__file__)
    bconfloader.applyDefaults(buildconf, True, projectDir)
    # check if applyDefaults produces validate params
    validateConf(buildconf)

    checkCommonDefaults(buildconf)

    assert hasattr(buildconf, 'buildroot')
    assert buildconf.buildroot == DEFAULT_BUILDROOTNAME

    assert buildconf.general == {
        'autoconfig': True,
        'db-format': 'pickle',
        'hash-algo': 'sha1',
    }

    assert buildconf.project == {
        'name' : 'tests', # name of directory with current test
        'version': '',
    }

    ######### not top-level

    buildconf = FakeBuildConf()
    projectDir = os.path.dirname(buildconf.__file__)
    bconfloader.applyDefaults(buildconf, False, projectDir)
    # check if applyDefaults produces validate params
    validateConf(buildconf)

    checkCommonDefaults(buildconf)

    assert buildconf.general == {}
    assert buildconf.project == {}

    ###################

    buildconf = FakeBuildConf()
    setattr(buildconf, 'general', { 'autoconfig' : False })
    bconfloader.applyDefaults(buildconf, True, '')
    assert buildconf.general == {
        'autoconfig': False,
        'db-format': 'pickle',
        'hash-algo': 'sha1',
    }

    buildconf = FakeBuildConf()
    buildtypes = {
        'debug' : {
            'toolchain' : 'g++',
            'cxxflags'  : ' -O0 -g',
            'linkflags' : '-Wl,--as-needed',
        },
    }
    setattr(buildconf, 'buildtypes', buildtypes)
    bconfloader.applyDefaults(buildconf, True, '')
    # check if applyDefaults produces validate params
    validateConf(buildconf)

    assert buildconf.buildtypes == buildtypes

def testLoad(monkeypatch, tmpdir):
    import sys
    from zm.waf.assist import isBuildConfFake

    buildconf = bconfloader.load()
    validateConf(buildconf)
    # It should be fake
    assert isBuildConfFake(buildconf)

    nonpath = os.path.join(cmn.randomstr(), cmn.randomstr())
    assert not os.path.exists(nonpath)
    buildconf = bconfloader.load(dirpath = nonpath)
    # It should be fake
    assert isBuildConfFake(buildconf)

    # invalidate conf
    monkeypatch.setattr(buildconf, 'tasks', 'something')
    with pytest.raises(ZenMakeConfError) as cm:
        buildconf = bconfloader.load()
        validateConf(buildconf)

    # find first real buildconf.py
    prjdir = None
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.py' in filenames:
            prjdir = dirpath
            break

    buildconf = bconfloader.load(dirpath = prjdir)
    validateConf(buildconf)
    assert not isBuildConfFake(buildconf)

    monkeypatch.syspath_prepend(os.path.abspath(prjdir))
    buildconf = bconfloader.load()
    validateConf(buildconf)
    assert not isBuildConfFake(buildconf)

    # find first real buildconf.yaml
    prjdir = None
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.yaml' in filenames:
            prjdir = dirpath
            break

    buildconf = bconfloader.load(dirpath = prjdir)
    validateConf(buildconf)
    assert not isBuildConfFake(buildconf)

    monkeypatch.syspath_prepend(os.path.abspath(prjdir))
    buildconf = bconfloader.load()
    validateConf(buildconf)
    assert not isBuildConfFake(buildconf)

    testdir = tmpdir.mkdir("load.yaml")
    yamlconf = testdir.join("buildconf.yaml")
    yamlconf.write("invalid data = {")
    with pytest.raises(ZenMakeConfError):
        buildconf = bconfloader.load(dirpath = str(testdir.realpath()))
    yamlconf.write("invalid data: {")
    with pytest.raises(ZenMakeConfError):
        buildconf = bconfloader.load(dirpath = str(testdir.realpath()))
