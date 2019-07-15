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
from waflib.Errors import WafError
import tests.common as cmn
import zm.buildconfutil

class FakeBuildConf:
    pass

class TestBuildconfUtil(object):

    def testValidateAll(self):
        buildconf = FakeBuildConf()
        setattr(buildconf, 'tasks', None)
        with pytest.raises(WafError):
            zm.buildconfutil.validateAll(buildconf)

    def testInitDefaults(self):

        buildconf = FakeBuildConf()
        zm.buildconfutil.initDefaults(buildconf)
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
        assert buildconf.buildtypes == {
            'debug' : {},
            'default': 'debug',
        }

        assert hasattr(buildconf, 'tasks')
        assert buildconf.tasks == {}

        assert hasattr(buildconf, 'buildroot')
        assert buildconf.buildroot == \
                            os.path.join(buildconf.project['root'], 'build')

        assert hasattr(buildconf, 'buildsymlink')
        assert buildconf.buildsymlink is None

        assert hasattr(buildconf, 'srcroot')
        assert buildconf.srcroot == buildconf.project['root']

        ###################

        buildconf = FakeBuildConf()
        setattr(buildconf, 'features', { 'autoconfig' : False })
        zm.buildconfutil.initDefaults(buildconf)
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
        zm.buildconfutil.initDefaults(buildconf)
        assert buildconf.buildtypes == buildtypes

    def testLoadConf(self, capsys, monkeypatch):
        import sys
        from zm.utils import stringtypes
        buildconf = zm.buildconfutil.loadConf()
        # It should be fake
        assert buildconf.__name__.endswith('fakebuildconf')

        # invalidate conf
        monkeypatch.setattr(buildconf, 'tasks', None)
        with pytest.raises(SystemExit) as cm:
            buildconf = zm.buildconfutil.loadConf()
        captured = capsys.readouterr()
        assert cm.value.code
        assert captured.err