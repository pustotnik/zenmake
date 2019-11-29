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
from zm.buildconf import loader as bconfloader

file = __file__

class FakeBuildConf:
    __name__ = 'testconf'
    __file__ = file

def checkCommonDefaults(buildconf):

    assert not hasattr(buildconf, 'startdir')
    assert not hasattr(buildconf, 'realbuildroot')

    assert hasattr(buildconf, 'options')
    assert buildconf.options == {}

    assert hasattr(buildconf, 'features')

    assert hasattr(buildconf, 'subdirs')
    assert buildconf.subdirs == []

    assert hasattr(buildconf, 'project')

    for param in ('toolchains', 'platforms', 'buildtypes', 'tasks'):
        assert hasattr(buildconf, param)
        assert getattr(buildconf, param) == {}

    assert hasattr(buildconf, 'matrix')
    assert buildconf.matrix == []

def testInitDefaults():

    ######### top-level

    buildconf = FakeBuildConf()
    projectDir = os.path.dirname(buildconf.__file__)
    bconfloader.applyDefaults(buildconf, True, projectDir)
    # check if applyDefaults produces validate params
    bconfloader.validate(buildconf)

    checkCommonDefaults(buildconf)

    assert hasattr(buildconf, 'buildroot')
    assert buildconf.buildroot == DEFAULT_BUILDROOTNAME

    assert buildconf.features == { 'autoconfig': True }

    assert buildconf.project == {
        'name' : 'tests', # name of directory with current test
        'version': '',
    }

    ######### not top-level

    buildconf = FakeBuildConf()
    projectDir = os.path.dirname(buildconf.__file__)
    bconfloader.applyDefaults(buildconf, False, projectDir)
    # check if applyDefaults produces validate params
    bconfloader.validate(buildconf)

    checkCommonDefaults(buildconf)

    assert buildconf.features == {}
    assert buildconf.project == {}

    ###################

    buildconf = FakeBuildConf()
    setattr(buildconf, 'features', { 'autoconfig' : False })
    bconfloader.applyDefaults(buildconf, True, '')
    assert buildconf.features == { 'autoconfig': False }

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
    bconfloader.validate(buildconf)

    assert buildconf.buildtypes == buildtypes

def testLoad(capsys, monkeypatch, tmpdir):
    import sys
    from zm.waf.assist import isBuildConfFake

    buildconf = bconfloader.load(check = False)
    buildconf = bconfloader.load(check = True)
    # It should be fake
    assert isBuildConfFake(buildconf)

    nonpath = os.path.join(cmn.randomstr(), cmn.randomstr())
    assert not os.path.exists(nonpath)
    buildconf = bconfloader.load(dirpath = nonpath)
    # It should be fake
    assert isBuildConfFake(buildconf)

    # invalidate conf
    monkeypatch.setattr(buildconf, 'tasks', 'something')
    with pytest.raises(SystemExit) as cm:
        buildconf = bconfloader.load()
    captured = capsys.readouterr()
    assert cm.value.code
    assert captured.err

    # find first real buildconf.py
    prjdir = None
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.py' in filenames:
            prjdir = dirpath
            break

    buildconf = bconfloader.load(dirpath = prjdir)
    assert not isBuildConfFake(buildconf)

    monkeypatch.syspath_prepend(os.path.abspath(prjdir))
    buildconf = bconfloader.load()
    assert not isBuildConfFake(buildconf)

    # find first real buildconf.yaml
    prjdir = None
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.yaml' in filenames:
            prjdir = dirpath
            break

    buildconf = bconfloader.load(dirpath = prjdir)
    assert not isBuildConfFake(buildconf)

    monkeypatch.syspath_prepend(os.path.abspath(prjdir))
    buildconf = bconfloader.load()
    assert not isBuildConfFake(buildconf)

    testdir = tmpdir.mkdir("load.yaml")
    yamlconf = testdir.join("buildconf.yaml")
    yamlconf.write("invalid data = {")
    with pytest.raises(ZenMakeConfError):
        buildconf = bconfloader.load(dirpath = str(testdir.realpath()))
    yamlconf.write("invalid data: {")
    with pytest.raises(ZenMakeConfError):
        buildconf = bconfloader.load(dirpath = str(testdir.realpath()))
