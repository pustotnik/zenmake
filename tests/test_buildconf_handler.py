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
from tests.common import asRealConf, randomstr
from zm.buildconf.handler import BuildConfHandler
from zm.buildconf.paths import BuildConfPaths
from zm import toolchains, utils
from zm.buildconf import loader as bconfloader
from zm.autodict import AutoDict
from zm.error import *
from zm.constants import *

joinpath = os.path.join

@pytest.mark.usefixtures("unsetEnviron")
class TestSuite(object):

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

        # CASE: buildconf.buildtypes.default
        buildconf = deepcopy(testingBuildConf)
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'mybuildtype'

        # CASE: buildconf.buildtypes.default is not valid in
        # buildconf.platforms
        buildconf = deepcopy(testingBuildConf)
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

        # CASE: buildconf.platforms[..].default
        buildconf = deepcopy(testingBuildConf)
        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['abc'], default = 'abc')
        })
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'abc'

        # CASE: buildconf.platforms[..].default doesn't exist
        buildconf = deepcopy(testingBuildConf)
        buildconf.platforms[PLATFORM].default = 'void'
        with pytest.raises(ZenMakeError):
            confHandler = BuildConfHandler(asRealConf(buildconf))
            bt = confHandler.defaultBuildType

        # CASE: global buildconf.matrix[..].default-buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            {
                'for' : {}, 'set' : { 'default-buildtype' : 'abc' }
            }
        ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'abc'

        # CASE: platform buildconf.matrix[..].default-buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            {
                'for' : { 'platform' : PLATFORM },
                'set' : { 'default-buildtype' : 'abc' }
            }
        ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'abc'
        buildconf.matrix = [
            {
                'for' : { 'platform' : PLATFORM + randomstr() },
                'set' : { 'default-buildtype' : 'abc' }
            }
        ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert confHandler.defaultBuildType == 'mybuildtype'

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

    def _checkSupportedBuildTypes(self, buildconf, expected):
        confHandler = BuildConfHandler(asRealConf(buildconf))
        assert sorted(confHandler.supportedBuildTypes) == sorted(expected)

    def testSupportedBuildTypes(self, testingBuildConf):
        buildconf = testingBuildConf

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}

        # CASE: buildtypes in buildconf.buildtypes
        buildconf = deepcopy(testingBuildConf)
        self._checkSupportedBuildTypes(buildconf, [
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
        self._checkSupportedBuildTypes(buildconf, [
            'mybuildtype', 'non-existent'
        ])

        # CASE: buildtypes in buildconf.buildtypes and non-empty value of
        # buildconf.platforms[PLATFORM] with valid values.
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.extrabtype = {}
        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'extrabtype' ]
        self._checkSupportedBuildTypes(buildconf, [
            'mybuildtype', 'extrabtype'
        ])

        # CASE: buildtypes in buildconf.buildtypes and non-empty value of
        # buildconf.platforms[PLATFORM] with valid values and default build type.
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.extrabtype = {}
        buildconf.buildtypes.default = 'mybuildtype'
        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'extrabtype' ]
        self._checkSupportedBuildTypes(buildconf, [
            'mybuildtype', 'extrabtype'
        ])

    def testSupportedBuildTypesMatrix(self, testingBuildConf):

        # CASE: no buildtypes in buildconf.buildtypes and global
        # buildtypes in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2' } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2' } },
            { 'for' : { 'buildtype' : ['b3', 'b2'] } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3' ])

        # CASE: no buildtypes in buildconf.buildtypes and platform
        # buildtypes in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b4 b2', 'platform' : PLATFORM } },
            { 'for' : { 'buildtype' : 'b5 b6', 'platform' : PLATFORM } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b4', 'b2', 'b5', 'b6' ])

        # CASE: no buildtypes in buildconf.buildtypes and global/platform
        # buildtypes in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b2', 'b3' ])

        # CASE: buildtypes in buildconf.buildtypes and global/platform
        # buildtypes in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.gb1 = {}
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2' } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'gb1', 'b1', 'b2' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'gb1', 'b1', 'b2' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'gb1', 'b2', 'b3' ])

        # CASE: buildtypes in buildconf.buildtypes, non-empty buildconf.platforms
        # and global/platform buildtypes in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.b1 = {}
        buildconf.buildtypes.b2 = {}
        buildconf.platforms[PLATFORM].valid = [ 'b1', 'b2' ]
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b3 b4' } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3', 'b4' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b3 b4', 'platform' : PLATFORM } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3', 'b4' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b5 b3', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b4 b3', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3', 'b4' ])
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1' } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2' ])


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

    def _checkTasks(self, buildconf, clicmd, expected):
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == expected
        # to force covering of cache
        assert confHandler.tasks == expected

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
        self._checkTasks(buildconf, clicmd, buildconf.tasks)

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

        self._checkTasks(buildconf, clicmd, expected)

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
        self._checkTasks(buildconf, clicmd, expected)

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
            self._checkTasks(buildconf, clicmd, expected)
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
            self._checkTasks(buildconf, clicmd, expected)
            monkeypatch.delenv(var, raising = False)

    def testTasksMatrix(self, testingBuildConf, monkeypatch):
        clicmd = AutoDict()
        clicmd.args.buildtype = 'mybt'
        baseMatrix = [
            { 'for' : { 'buildtype' : 'mybt' }  },
        ]

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : { 'task' : 't1' }, 'set' : { 'param1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'param2' : '2' } },
        ]
        expected = { 't1': {'param1': '1'}, 't2': {'param2': '2'} }
        self._checkTasks(buildconf, clicmd, expected)

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # No param 'default-buildtype' in resulting tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : { 'task' : 't1' }, 'set' : { 'param1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'param2' : '2' } },
            { 'for' : {}, 'set' : { 'default-buildtype' : 'mybt' } },
        ]
        self._checkTasks(buildconf, clicmd, {
            't1': {'param1': '1'}, 't2': {'param2': '2'}
        })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # with non-empty selected buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            {
                'for' : { 'task' : 't1', 'buildtype' : 'b1 b2', },
                'set' : { 'param1' : '1' }
            },
            {
                'for' : { 'task' : 't2', 'buildtype' : 'mybt', },
                'set' : { 'param2' : '2' }
            },
        ]
        self._checkTasks(buildconf, clicmd, { 't1': {}, 't2': {'param2': '2'} })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # Applying for all tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p2' : '2' } },
        ]
        self._checkTasks(buildconf, clicmd, {
            't1': {'p1': '1', 'p3': '3'},
            't2': {'p2': '2', 'p3': '3'},
        })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # Merging/replacing params in tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p1' : '1', 'p2' : '2' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p2' : '22' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p4' : '4', 'p2' : '-2-' } },
        ]
        self._checkTasks(buildconf, clicmd, {
            't1': {'p1': '1', 'p3': '3', 'p2' : '-2-', 'p4' : '4'},
            't2': {'p2': '22', 'p3': '3'},
        })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # with non-empty platform
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            {
                'for' : { 'task' : 't1', },
                'set' : { 'p1' : '1' }
            },
            {
                'for' : { 'task' : 't2', 'platform' : PLATFORM, },
                'set' : { 'p2' : '2' }
            },
        ]
        expected = { 't1': {'p1': '1'}, 't2': {'p2': '2'} }
        self._checkTasks(buildconf, clicmd, expected)
        buildconf.matrix = baseMatrix + [
            {
                'for' : { 'task' : 't1', 'platform' : PLATFORM },
                'set' : { 'p1' : '1' }
            },
            {
                'for' : { 'task' : 't2', 'platform' : PLATFORM + randomstr(), },
                'set' : { 'p2' : '2' }
            },
        ]
        expected = { 't1': {'p1': '1'}, 't2': {} }
        self._checkTasks(buildconf, clicmd, expected)

        # CASE: some tasks in buildconf.tasks, some tasks in buildconf.matrix
        # complex merging
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.t1.p1 = '1'
        buildconf.tasks.t2.p2 = '2'
        buildconf.tasks.t2.p3 = '2'
        buildconf.matrix = baseMatrix + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't3' }, 'set' : { 'p1' : '1', 'p2' : '2' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p1' : '11' } },
            { 'for' : { 'task' : 't4' }, 'set' : { 'p5' : '1', 'p6' : '2' } },
        ]
        self._checkTasks(buildconf, clicmd, {
            't1': {'p1': '1', 'p3': '3'},
            't2': {'p1': '11', 'p2': '2', 'p3': '3'},
            't3': {'p1': '1', 'p2': '2', 'p3': '3'},
            't4': {'p5': '1', 'p6': '2', 'p3': '3'},
        })

    def _checkToolchainNames(self, buildconf, clicmd, expected):
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        assert sorted(confHandler.toolchainNames) == sorted(expected)
        # to force covering of cache
        assert sorted(confHandler.toolchainNames) == sorted(expected)

    def testToolchainNames(self, testingBuildConf):

        buildconf = testingBuildConf

        # CASE: invalid use
        confHandler = BuildConfHandler(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            empty = confHandler.toolchainNames

        buildconf.buildtypes['debug-gxx'] = {}
        clicmd = AutoDict()
        clicmd.args.buildtype = 'debug-gxx'

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
        self._checkToolchainNames(buildconf, clicmd, ['gxx'])

        # CASE: tasks with different toolchains
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.toolchain = 'gxx'
        buildconf.tasks.test2.toolchain = 'lgxx'
        self._checkToolchainNames(buildconf, clicmd, ['gxx', 'lgxx'])

        ### matrix

        # CASE: empty toolchains in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            {
                'for' : { 'task' : 'test1' },
                'set' : { 'param1' : '11', 'param2' : '22' }
            },
        ]
        confHandler = BuildConfHandler(asRealConf(buildconf))
        confHandler.handleCmdLineArgs(clicmd)
        # it returns tuple but it can return list so we check by len
        assert len(confHandler.toolchainNames) == 0

        # CASE: tasks in matrix with the same toolchain
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            { 'for' : { 'task' : 'test1' }, 'set' : { 'toolchain' : 'gxx' } },
            { 'for' : { 'task' : 'test2' }, 'set' : { 'toolchain' : 'gxx' } },
        ]
        self._checkToolchainNames(buildconf, clicmd, ['gxx'])

        # CASE: tasks in matrix with the different toolchains
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            { 'for' : { 'task' : 'test1' }, 'set' : { 'toolchain' : 'gxx' } },
            { 'for' : { 'task' : 'test2' }, 'set' : { 'toolchain' : 'lgxx' } },
        ]
        self._checkToolchainNames(buildconf, clicmd, ['gxx', 'lgxx'])


    def testCustomToolchains(self, testingBuildConf, capsys):
        buildconf = testingBuildConf

        buildconf.buildtypes['debug-gxx'] = {}
        clicmd = AutoDict()
        clicmd.args.buildtype = 'debug-gxx'

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
