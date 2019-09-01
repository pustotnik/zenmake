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
from zm.buildconf import loader as bconfloader

class FakeBuildConf:
    __name__ = 'testconf'

def testInitDefaults():

    buildconf = FakeBuildConf()
    bconfloader.initDefaults(buildconf)
    # check if initDefaults produces validate params
    bconfloader.validate(buildconf)

    assert hasattr(buildconf, 'features')
    assert buildconf.features == { 'autoconfig': True }

    assert hasattr(buildconf, 'project')
    assert buildconf.project == {
        'root' : os.curdir,
        'name' : 'NONAME',
        'version': '0.0.0.0',
    }

    assert hasattr(buildconf, 'toolchains')
    assert buildconf.toolchains == {}

    assert hasattr(buildconf, 'platforms')
    assert buildconf.platforms == {}

    assert hasattr(buildconf, 'buildtypes')

    assert hasattr(buildconf, 'tasks')
    assert buildconf.tasks == {}

    assert hasattr(buildconf, 'buildroot')
    assert buildconf.buildroot == \
                        os.path.join(buildconf.project['root'], 'build')

    assert hasattr(buildconf, 'realbuildroot')
    assert buildconf.realbuildroot == buildconf.buildroot

    assert hasattr(buildconf, 'srcroot')
    assert buildconf.srcroot == buildconf.project['root']

    ###################

    buildconf = FakeBuildConf()
    setattr(buildconf, 'features', { 'autoconfig' : False })
    bconfloader.initDefaults(buildconf)
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
    bconfloader.initDefaults(buildconf)
    # check if initDefaults produces validate params
    bconfloader.validate(buildconf)

    assert buildconf.buildtypes == buildtypes

def testLoad(capsys, monkeypatch, tmpdir):
    import sys
    from zm.assist import isBuildConfFake

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
