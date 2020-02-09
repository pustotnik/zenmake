# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = too-many-statements, protected-access, unused-variable

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from copy import deepcopy
import pytest

from zm.autodict import AutoDict
from zm.error import *
from zm.constants import *
from zm import utils
from zm.features import ToolchainVars
from zm.buildconf.processing import Config as BuildConfig
from tests.common import asRealConf, randomstr

joinpath = os.path.join

@pytest.mark.usefixtures("unsetEnviron")
class TestSuite(object):

    def testInit(self, testingBuildConf):
        buildconf = testingBuildConf
        conf = asRealConf(buildconf)
        bconf = BuildConfig(conf)
        with pytest.raises(ZenMakeError):
            btype = bconf.selectedBuildType
        assert bconf._conf == conf
        assert bconf.projectName == buildconf.project.name
        assert bconf.projectVersion == buildconf.project.version

    def testDefaultBuildType(self, testingBuildConf):
        buildconf = testingBuildConf

        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == ''

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abc = {}
        buildconf.buildtypes.default = 'mybuildtype'

        # CASE: buildconf.buildtypes.default
        buildconf = deepcopy(testingBuildConf)
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'mybuildtype'

        # CASE: buildconf.buildtypes.default is not valid in
        # buildconf.platforms
        buildconf = deepcopy(testingBuildConf)
        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['abc'], )
        })
        with pytest.raises(ZenMakeError):
            bconf = BuildConfig(asRealConf(buildconf))
            bt = bconf.defaultBuildType
        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['mybuildtype'], )
        })
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'mybuildtype'

        # CASE: buildconf.platforms[..].default
        buildconf = deepcopy(testingBuildConf)
        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['abc'], default = 'abc')
        })
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'abc'

        # CASE: buildconf.platforms[..].default doesn't exist
        buildconf = deepcopy(testingBuildConf)
        buildconf.platforms[PLATFORM].default = 'void'
        with pytest.raises(ZenMakeError):
            bconf = BuildConfig(asRealConf(buildconf))
            bt = bconf.defaultBuildType

        # CASE: global buildconf.matrix[..].default-buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            {
                'for' : {}, 'set' : { 'default-buildtype' : 'abc' }
            }
        ]
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'abc'

        # CASE: platform buildconf.matrix[..].default-buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = [
            {
                'for' : { 'platform' : PLATFORM },
                'set' : { 'default-buildtype' : 'abc' }
            }
        ]
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'abc'
        buildconf.matrix = [
            {
                'for' : { 'platform' : PLATFORM + randomstr() },
                'set' : { 'default-buildtype' : 'abc' }
            }
        ]
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'mybuildtype'

    def testSelectedBuildType(self, testingBuildConf):
        buildconf = testingBuildConf
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        bconf = BuildConfig(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            bt = bconf.selectedBuildType

        buildtype = 'mybuildtype'
        bconf.applyBuildType(buildtype)
        assert bconf.selectedBuildType == buildtype

    def _checkSupportedBuildTypes(self, buildconf, expected):
        bconf = BuildConfig(asRealConf(buildconf))
        assert sorted(bconf.supportedBuildTypes) == sorted(expected)

    def testSupportedBuildTypes(self, testingBuildConf):
        buildconf = testingBuildConf

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}
        buildconf.buildtypes.default = 'mybuildtype'

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
            bconf = BuildConfig(asRealConf(buildconf))
            empty = bconf.supportedBuildTypes

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

        buildconf = testingBuildConf
        buildconf.buildtypes.default = 'b1'

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
        buildconf.buildtypes.default = 'b2'
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
        buildconf.buildtypes.default = 'b2'
        buildconf.matrix = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b2', 'b3' ])

        # CASE: buildtypes in buildconf.buildtypes and global/platform
        # buildtypes in matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.gb1 = {}
        buildconf.buildtypes.default = 'b2'
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


    def testApplyBuildType(self, testingBuildConf):

        buildtype = 'mybuildtype'

        buildconf = testingBuildConf
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        bconf = BuildConfig(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            bt = bconf.selectedBuildType

        with pytest.raises(ZenMakeError):
            bconf.applyBuildType(None)

        bconf.applyBuildType(buildtype)
        # Hm, all other results of this method is checked in testSupportedBuildTypes
        assert bconf.selectedBuildType

    def _checkTasks(self, buildconf, buildtype, expected):
        bconf = BuildConfig(asRealConf(buildconf))
        bconf.applyBuildType(buildtype)

        expected = expected.copy()
        for task in expected:
            expected[task]['$startdir'] = '.'
        assert bconf.tasks == expected
        # to force covering of cache
        assert bconf.tasks == expected

    def testTasks(self, testingBuildConf, monkeypatch):
        buildconf = testingBuildConf

        # CASE: invalid use
        bconf = BuildConfig(asRealConf(buildconf))
        with pytest.raises(ZenMakeLogicError):
            empty = bconf.tasks

        buildconf.buildtypes.default = 'mybuildtype'
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}
        buildtype = 'mybuildtype'

        # CASE: just empty buildconf.tasks
        buildconf = deepcopy(testingBuildConf)
        bconf = BuildConfig(asRealConf(buildconf))
        bconf.applyBuildType(buildtype)
        assert bconf.tasks == {}
        # this assert just for in case
        assert bconf.selectedBuildType == 'mybuildtype'

        # CASE: just some buildconf.tasks, nothing else
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '1'
        buildconf.tasks.test2.param2 = '2'
        self._checkTasks(buildconf, buildtype, buildconf.tasks)

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

        self._checkTasks(buildconf, buildtype, expected)

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
        self._checkTasks(buildconf, buildtype, expected)

        # CASE: influence of compiler flags from system environment
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '111'
        buildconf.tasks.test2.param2 = '222'

        testOldVal = 'val1 val2'
        testNewVal = 'val11 val22'
        testNewValAsList = utils.toList(testNewVal)
        flagVars = ToolchainVars.allFlagVars()
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
            self._checkTasks(buildconf, buildtype, expected)
            monkeypatch.delenv(var, raising = False)

        # CASE: influence of compiler var from system environment
        buildconf = deepcopy(testingBuildConf)
        testOldVal = 'old-compiler'
        testNewVal = 'new-compiler'
        toolchainVars = ToolchainVars.allVarsToSetToolchain()
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
            self._checkTasks(buildconf, buildtype, expected)
            monkeypatch.delenv(var, raising = False)

    def testTasksMatrix(self, testingBuildConf):

        buildtype = 'mybt'
        baseMatrix = [
            { 'for' : { 'buildtype' : 'mybt' }  },
        ]
        testingBuildConf.buildtypes.default = 'mybt'

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : { 'task' : 't1' }, 'set' : { 'param1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'param2' : '2' } },
        ]
        expected = { 't1': {'param1': '1'}, 't2': {'param2': '2'} }
        self._checkTasks(buildconf, buildtype, expected)

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # No param 'default-buildtype' in resulting tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : { 'task' : 't1' }, 'set' : { 'param1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'param2' : '2' } },
            { 'for' : {}, 'set' : { 'default-buildtype' : 'mybt' } },
        ]
        self._checkTasks(buildconf, buildtype, {
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
        self._checkTasks(buildconf, buildtype, { 't1': {}, 't2': {'param2': '2'} })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.matrix
        # Applying for all tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.matrix = baseMatrix + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p2' : '2' } },
        ]
        self._checkTasks(buildconf, buildtype, {
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
        self._checkTasks(buildconf, buildtype, {
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
        self._checkTasks(buildconf, buildtype, expected)
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
        self._checkTasks(buildconf, buildtype, expected)

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
        self._checkTasks(buildconf, buildtype, {
            't1': {'p1': '1', 'p3': '3'},
            't2': {'p1': '11', 'p2': '2', 'p3': '3'},
            't3': {'p1': '1', 'p2': '2', 'p3': '3'},
            't4': {'p5': '1', 'p6': '2', 'p3': '3'},
        })

    def testCustomToolchains(self, testingBuildConf, capsys):
        buildconf = testingBuildConf

        buildconf.buildtypes['debug-gxx'] = {}
        buildconf.buildtypes.default = 'debug-gxx'

        # CASE: no custom toolchains
        buildconf = deepcopy(testingBuildConf)
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.customToolchains == {}

        # CASE: invalid toolchain
        buildconf = deepcopy(testingBuildConf)
        buildconf.toolchains = {
            'something' : {}
        }
        bconf = BuildConfig(asRealConf(buildconf))
        with pytest.raises(ZenMakeError):
            empty = bconf.customToolchains

        # CASE: one custom toolchain with fake path
        buildconf = deepcopy(testingBuildConf)
        buildconf.toolchains = {
            'something' : {
                'kind': 'auto-c++',
                'var': joinpath('path', 'to', 'toolchain')
            },
        }
        bconf = BuildConfig(asRealConf(buildconf))
        confPaths = bconf.confPaths
        expected = deepcopy(buildconf.toolchains)
        expected['something']['vars'] = {
            'var' : utils.unfoldPath(confPaths.startdir,
                                     buildconf.toolchains['something']['var'])
        }
        del expected['something']['var']
        assert bconf.customToolchains == expected
        captured = capsys.readouterr()
        assert "doesn't exist" in captured.err
        # to force covering of cache
        assert bconf.customToolchains == expected
