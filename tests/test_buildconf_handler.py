# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from copy import deepcopy
import pytest
from tests.common import asRealConf
from zm.buildconf.handler import BuildConfHandler
from zm.buildconf.paths import BuildConfPaths
from zm import toolchains, utils
from zm.buildconf import loader as bconfloader
from zm.autodict import AutoDict
from zm.error import *
from zm.constants import *

joinpath = os.path.join

@pytest.mark.usefixtures("unsetEnviron")
class TestBuildConfHandler(object):

    def testInit(self, testingBuildConf):
        buildconf = testingBuildConf
        conf = asRealConf(buildconf)
        confHandler = BuildConfHandler(conf)
        assert not confHandler.cmdLineHandled
        assert confHandler.conf == conf
        assert confHandler.projectName == buildconf.project.name
        assert confHandler.projectVersion == buildconf.project.version
        assert confHandler.confPaths == BuildConfPaths(buildconf)

    def testDefaultBuildType(self, testingBuildConf):
        buildconf = testingBuildConf

        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == ''

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abc = {}
        buildconf.buildtypes.default = 'mybuildtype'
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'mybuildtype'

        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['abc'], )
        })
        with pytest.raises(ZenMakeError):
            confHandler = BuildConfHandler(asRealConf(buildconf))
            bt = confHandler.defaultBuildType
        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['mybuildtype'], )
        })
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'mybuildtype'

        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['abc'], default = 'abc')
        })
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'abc'

        buildconf.platforms[PLATFORM].default = 'void'
        with pytest.raises(ZenMakeError):
            confHandler = BuildConfHandler(asRealConf(buildconf))
            bt = confHandler.defaultBuildType

    def testSelectedBuildType(self, testingBuildConf):
        buildconf = testingBuildConf
        clicmd = AutoDict()

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        confHandler = BuildConfHandler(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            bt = confHandler.selectedBuildType

        clicmd.args.buildtype = 'mybuildtype'
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.selectedBuildType == clicmd.args.buildtype

    def testSupportedBuildTypes(self, testingBuildConf):
        buildconf = testingBuildConf

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}

        # save base fixture
        buildconf = deepcopy(testingBuildConf)

        # CASE: buildtypes in buildconf.buildtypes
        buildconf = deepcopy(testingBuildConf)
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'abcbt'
        ])

        # CASE: buildtypes in buildconf.buildtypes and empty value of
        # buildconf.platforms[PLATFORM]
        buildconf = deepcopy(testingBuildConf)
        buildconf.platforms[PLATFORM] = AutoDict()
        with pytest.raises(ZenMakeError):
            confHandler = BuildConfHandler(asRealConf(buildconf))
            empty = confHandler.supportedBuildTypes

        # CASE: buildtypes in buildconf.buildtypes and non-empty value of
        # buildconf.platforms[PLATFORM] with non-existent value.
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.extrabtype = {}
        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'non-existent' ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'non-existent'
        ])

        # CASE: buildtypes in buildconf.buildtypes and non-empty value of
        # buildconf.platforms[PLATFORM] with valid values.
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.extrabtype = {}
        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'extrabtype' ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'extrabtype'
        ])

        # CASE: buildtypes in buildconf.buildtypes and non-empty value of
        # buildconf.platforms[PLATFORM] with valid values and default build type.
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.extrabtype = {}
        buildconf.buildtypes.default = 'mybuildtype'
        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'extrabtype' ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'extrabtype'
        ])

    def testHandleCmdLineArgs(self, testingBuildConf):

        clicmd = AutoDict()
        clicmd.args.buildtype = 'mybuildtype'

        fakeBuildConf = utils.loadPyModule('zm.buildconf.fakeconf', withImport = False)
        bconfloader.initDefaults(fakeBuildConf)
        confHandler = BuildConfHandler(fakeBuildConf)
        with pytest.raises(ZenMakeError):
            confHandler.handleCmdLineArgs(clicmd)

        buildconf = testingBuildConf
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert not confHandler.cmdLineHandled

        with pytest.raises(ZenMakeError):
            confHandler.handleCmdLineArgs(AutoDict())

        confHandler.handleCmdLineArgs(clicmd)
        # Hm, all other results of this method is checked in testSupportedBuildTypes
        assert confHandler.cmdLineHandled

    def testTasks(self, testingBuildConf, monkeypatch):
        buildconf = testingBuildConf

        # CASE: invalid use
        confHandler = BuildConfHandler(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            empty = confHandler.tasks

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}
        clicmd = AutoDict()
        clicmd.args.buildtype = 'mybuildtype'

        # save base fixture
        buildconf = deepcopy(testingBuildConf)

        # CASE: just empty buildconf.tasks
        buildconf = deepcopy(testingBuildConf)
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == {}
        # this assert just for in case
        assert confHandler.selectedBuildType == 'mybuildtype'

        # CASE: just some buildconf.tasks, nothing else
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '1'
        buildconf.tasks.test2.param2 = '2'
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        # to force covering of cache
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == buildconf.tasks
        # to force covering of cache
        assert confHandler.tasks == buildconf.tasks

        # CASE: some buildconf.tasks and buildconf.buildtypes
        # with non-empty selected buildtype
        # buildtype 'mybuildtype' should be selected at this moment
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '111'
        buildconf.tasks.test2.param2 = '222'
        buildconf.buildtypes.mybuildtype = { 'cxxflags' : '-O2' }

        expected = deepcopy(buildconf.tasks)
        for task in expected:
            expected[task].update(deepcopy(buildconf.buildtypes.mybuildtype))
        # self checking
        assert expected.test1.cxxflags == '-O2'
        assert expected.test2.cxxflags == '-O2'

        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == expected

        # CASE: some buildconf.tasks and buildconf.buildtypes
        # with non-empty selected buildtype. Both have some same params and
        # params from buildconf.buildtypes must override params from
        # buildconf.tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = 'p1'
        buildconf.tasks.test2.cxxflags = '-Os'
        buildconf.tasks.test2.toolchain = 'auto-c'
        buildconf.buildtypes.mybuildtype = {
            'cxxflags' : '-O2',
            'toolchain' : 'gcc',
        }
        expected = deepcopy(buildconf.tasks)
        for task in expected:
            expected[task].update(deepcopy(buildconf.buildtypes.mybuildtype))
        # self checking
        assert expected.test1.cxxflags == '-O2'
        assert expected.test2.cxxflags == '-O2'
        assert expected.test1.toolchain == 'gcc'
        assert expected.test2.toolchain == 'gcc'
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == expected

        # CASE: influence of compiler flags from system environment
        cinfo = toolchains.CompilersInfo

        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '111'
        buildconf.tasks.test2.param2 = '222'

        testOldVal = 'val1 val2'
        testNewVal = 'val11 val22'
        testNewValAsList = utils.toList(testNewVal)
        flagVars = cinfo.allFlagVars()
        for var in flagVars:
            param = var.lower()
            buildconf.buildtypes.mybuildtype = { param : testOldVal }
            expected = deepcopy(buildconf.tasks)
            for task in expected:
                expected[task].update({ param : testNewValAsList })
            # self checking
            assert expected.test1[param] == testNewValAsList
            assert expected.test2[param] == testNewValAsList
            monkeypatch.setenv(var, testNewVal)

            confHandler = BuildConfHandler(asRealConf(buildconf))
            confHandler.handleCmdLineArgs(clicmd)
            assert confHandler.tasks == expected

            monkeypatch.delenv(var, raising = False)

        # CASE: influence of compiler var from system environment
        cinfo = toolchains.CompilersInfo
        buildconf = deepcopy(testingBuildConf)
        testOldVal = 'old-compiler'
        testNewVal = 'new-compiler'
        toolchainVars = cinfo.allVarsToSetCompiler()
        for var in toolchainVars:
            param = var.lower()
            buildconf.tasks.test1.features = ''
            buildconf.tasks.test1.toolchain = testOldVal
            buildconf.tasks.test2.features = param
            buildconf.tasks.test2.toolchain = testOldVal
            expected = deepcopy(buildconf.tasks)
            expected.test1.toolchain = testOldVal
            expected.test2.toolchain = testNewVal

            monkeypatch.setenv(var, testNewVal)

            confHandler = BuildConfHandler(asRealConf(buildconf))
            confHandler.handleCmdLineArgs(clicmd)
            assert confHandler.tasks == expected

            monkeypatch.delenv(var, raising = False)

    def testToolchainNames(self, testingBuildConf):
        buildconf = testingBuildConf

        # CASE: invalid use
        confHandler = BuildConfHandler(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            empty = confHandler.toolchainNames

        buildconf.buildtypes['debug-gxx'] = {}
        clicmd = AutoDict()
        clicmd.args.buildtype = 'debug-gxx'

        # save base fixture
        buildconf = deepcopy(testingBuildConf)

        # CASE: just empty toolchains
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '111'
        buildconf.tasks.test2.param2 = '222'
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        # it returns tuple but it can return list so we check by len
        assert len(confHandler.toolchainNames) == 0

        # CASE: tasks with the same toolchain
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.toolchain = 'gxx'
        buildconf.tasks.test2.toolchain = 'gxx'
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert list(confHandler.toolchainNames) == ['gxx']
        # to force covering of cache
        assert list(confHandler.toolchainNames) == ['gxx']

        # CASE: tasks with different toolchains
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.toolchain = 'gxx'
        buildconf.tasks.test2.toolchain = 'lgxx'
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert sorted(confHandler.toolchainNames) == sorted(['gxx', 'lgxx'])

    def testCustomToolchains(self, testingBuildConf, capsys):
        buildconf = testingBuildConf

        buildconf.buildtypes['debug-gxx'] = {}
        clicmd = AutoDict()
        clicmd.args.buildtype = 'debug-gxx'

        # save base fixture
        buildconf = deepcopy(testingBuildConf)

        # CASE: no custom toolchains
        buildconf = deepcopy(testingBuildConf)
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.customToolchains == {}

        # CASE: invalid toolchain
        buildconf = deepcopy(testingBuildConf)
        buildconf.toolchains = {
            'something' : {}
        }
        confHandler = BuildConfHandler(asRealConf(buildconf))
        with pytest.raises(ZenMakeError):
            empty = confHandler.customToolchains

        # CASE: one custom toolchain with fake path
        buildconf = deepcopy(testingBuildConf)
        buildconf.toolchains = {
            'something' : {
                'kind': 'auto-c++',
                'var': joinpath('path', 'to', 'toolchain')
            },
        }
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confPaths = confHandler.confPaths
        expected = deepcopy(buildconf.toolchains)
        expected['something']['vars'] = {
            'var' : utils.unfoldPath(confPaths.projectroot,
                                     buildconf.toolchains['something']['var'])
        }
        del expected['something']['var']
        assert confHandler.customToolchains == expected
        captured = capsys.readouterr()
        assert "doesn't exists" in captured.err
        # to force covering of cache
        assert confHandler.customToolchains == expected
