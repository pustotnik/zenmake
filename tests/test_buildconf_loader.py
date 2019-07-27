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
from zm.constants import KNOWN_PLATFORMS
import tests.common as cmn
from zm.buildconf import loader as bconfloader
from zm.buildconf.loader import KNOWN_TOOLCHAIN_KINDS

class FakeBuildConf:
    __name__ = 'testconf'

class TestBuildconfUtil(object):

    def _checkAttrAsDict(self, buildconf, attrName):
        setattr(buildconf, attrName, cmn.randomint())
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        setattr(buildconf, attrName, cmn.randomstr())
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        setattr(buildconf, attrName, [])
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        setattr(buildconf, attrName, {})
        bconfloader.validate(buildconf)

    def _checkParamAsDict(self, buildconf, confnode, paramName):
        confnode[paramName] = cmn.randomint()
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        confnode[paramName] = cmn.randomstr()
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        confnode[paramName] = []
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        confnode[paramName] =  {}
        bconfloader.validate(buildconf)

    def _checkParamsAsStr(self, buildconf, confnode, paramNames, validVals = []):
        for param in paramNames:
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = [cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = [cmn.randomstr(), cmn.randomstr()]
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            if not validVals:
                confnode[param] = cmn.randomstr()
                bconfloader.validate(buildconf)
            else:
                invalid = validVals[0] + cmn.randomstr()
                confnode[param] = invalid
                with pytest.raises(ZenMakeConfValueError):
                    bconfloader.validate(buildconf)
                for v in validVals:
                    confnode[param] = v
                    bconfloader.validate(buildconf)

    def _checkParamsAsListOfStrs(self, buildconf, confnode, paramNames, validVals = []):
        for param in paramNames:
            confnode[param] = {}
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = cmn.randomstr()
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = [cmn.randomstr(), cmn.randomint(), cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            if not validVals:
                confnode[param] = [cmn.randomstr(), cmn.randomstr()]
                bconfloader.validate(buildconf)
                confnode[param] = (cmn.randomstr(), cmn.randomstr())
                bconfloader.validate(buildconf)
            else:
                invalid = str(validVals[0]) + cmn.randomstr()
                confnode[param] = [invalid]
                with pytest.raises(ZenMakeConfValueError):
                    bconfloader.validate(buildconf)
                confnode[param] = validVals
                bconfloader.validate(buildconf)

    def _checkParamsAsStrOrListOfStrs(self, buildconf, confnode, paramNames, validVals = []):
        for param in paramNames:
            confnode[param] = {}
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            confnode[param] = [cmn.randomstr(), cmn.randomint(), cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            if not validVals:
                confnode[param] = cmn.randomstr()
                bconfloader.validate(buildconf)
                confnode[param] = [cmn.randomstr(), cmn.randomstr()]
                bconfloader.validate(buildconf)
                confnode[param] = (cmn.randomstr(), cmn.randomstr())
                bconfloader.validate(buildconf)
            else:
                invalid = str(validVals[0]) + cmn.randomstr()
                confnode[param] = invalid
                with pytest.raises(ZenMakeConfValueError):
                    bconfloader.validate(buildconf)
                confnode[param] = [invalid]
                with pytest.raises(ZenMakeConfValueError):
                    bconfloader.validate(buildconf)
                for v in validVals:
                    confnode[param] = v
                    bconfloader.validate(buildconf)
                confnode[param] = validVals
                bconfloader.validate(buildconf)

    def testValidateParamStrs(self):

        for param in ('buildroot', 'buildsymlink', 'srcroot'):
            buildconf = FakeBuildConf()
            setattr(buildconf, param, 11)
            with pytest.raises(ZenMakeConfTypeError):
                bconfloader.validate(buildconf)
            setattr(buildconf, param, cmn.randomstr())
            bconfloader.validate(buildconf)

    def testValidateParamFeatures(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'features')

        setattr(buildconf, 'features', { 'autoconfig' : 1 })
        with pytest.raises(ZenMakeConfTypeError):
            bconfloader.validate(buildconf)
        setattr(buildconf, 'features', { 'autoconfig' : False })
        bconfloader.validate(buildconf)
        setattr(buildconf, 'features', { 'autoconfig' : False, 'unknown': 1 })
        bconfloader.validate(buildconf)

    def testValidateParamProject(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'project')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'project', {})
        paramNames = ('name', 'version', 'root')
        self._checkParamsAsStr(buildconf, buildconf.project, paramNames)

    def testValidateParamBuildtypes(self):

        btypeNames = [cmn.randomstr() for i in range(4)]

        #####
        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'buildtypes')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'buildtypes', {})
        for btype in btypeNames:
            buildconf.buildtypes[btype] = {}
            self._checkParamAsDict(buildconf, buildconf.buildtypes, btype)
        paramNames = ('default',)
        self._checkParamsAsStr(buildconf, buildconf.buildtypes,
                                paramNames, btypeNames)

        #####
        buildconf = FakeBuildConf()
        setattr(buildconf, 'buildtypes', {})
        setattr(buildconf, 'tasks', {})
        taskNames = [cmn.randomstr() for i in range(4)]
        buildconf.tasks[taskNames[0]] = {
            'buildtypes' : { btypeNames[0] : {} }
        }
        buildconf.tasks[taskNames[2]] = {
            'buildtypes' : { btypeNames[3] : {} }
        }
        buildconf.buildtypes['default'] = btypeNames[0]
        bconfloader.validate(buildconf)
        buildconf.buildtypes['default'] = btypeNames[1]
        with pytest.raises(ZenMakeConfValueError):
            bconfloader.validate(buildconf)
        buildconf.buildtypes['default'] = btypeNames[2]
        with pytest.raises(ZenMakeConfValueError):
            bconfloader.validate(buildconf)
        buildconf.buildtypes['default'] = btypeNames[3]
        bconfloader.validate(buildconf)

        #####
        buildconf = FakeBuildConf()
        setattr(buildconf, 'buildtypes', {
            'default': 'testbtype',
            'testbtype' : {}
        })
        self._checkParamsAsStr(buildconf, buildconf.buildtypes['testbtype'],
                               ['toolchain'], KNOWN_TOOLCHAIN_KINDS)
        paramNames = ('cflags', 'cxxflags', 'cppflags', 'linkflags', 'defines')
        self._checkParamsAsStrOrListOfStrs(
                        buildconf, buildconf.buildtypes['testbtype'], paramNames)

    def testValidateParamToolchains(self):

        toolNames = [cmn.randomstr() for i in range(3)]

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'toolchains')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'toolchains', {})
        for tool in toolNames:
            buildconf.toolchains[tool] = {}
            bconfloader.validate(buildconf)
            self._checkParamAsDict(buildconf, buildconf.toolchains, tool)
            self._checkParamsAsStr(buildconf, buildconf.toolchains[tool],
                               ['kind'], KNOWN_TOOLCHAIN_KINDS)
            paramNames = [cmn.randomstr() for i in range(10)]
            for param in paramNames:
                assert param != 'kind'
            self._checkParamsAsStr(buildconf, buildconf.toolchains[tool],
                                   paramNames)

        buildconf = FakeBuildConf()
        setattr(buildconf, 'toolchains', {})
        for tool in toolNames:
            buildconf.toolchains[tool] = {}
        setattr(buildconf, 'buildtypes', {
            'testbtype' : {}
        })

        self._checkParamsAsStr(buildconf, buildconf.buildtypes['testbtype'],
                               ['toolchain'], KNOWN_TOOLCHAIN_KINDS + toolNames)

    def testValidateParamPlatforms(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'platforms')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'platforms', {
            KNOWN_PLATFORMS[0] + cmn.randomstr() : {}
        })
        with pytest.raises(ZenMakeConfValueError):
            bconfloader.validate(buildconf)
        setattr(buildconf, 'platforms', {
            KNOWN_PLATFORMS[0] + cmn.randomstr() : {},
            KNOWN_PLATFORMS[1] + cmn.randomstr() : {},
        })
        with pytest.raises(ZenMakeConfValueError):
            bconfloader.validate(buildconf)
        setattr(buildconf, 'platforms', {})
        for _platform in KNOWN_PLATFORMS:
            buildconf.platforms[_platform] = {}
        bconfloader.validate(buildconf)

        buildconf = FakeBuildConf()
        setattr(buildconf, 'platforms', {})
        for _platform in KNOWN_PLATFORMS:
            buildconf.platforms[_platform] = {}
            self._checkParamsAsListOfStrs(
                        buildconf, buildconf.platforms[_platform], ['valid'])
            self._checkParamsAsStr(
                        buildconf, buildconf.platforms[_platform], ['default'])

    def testInitDefaults(self):

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

        assert hasattr(buildconf, 'buildsymlink')
        assert buildconf.buildsymlink is None

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

    def testLoad(self, capsys, monkeypatch):
        import sys
        from zm.assist import isBuildConfFake
        buildconf = bconfloader.load(withImport = False)
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

        buildconf = bconfloader.load(dirpath = prjdir, withImport = False)
        assert not isBuildConfFake(buildconf)
