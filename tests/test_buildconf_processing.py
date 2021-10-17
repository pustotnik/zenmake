# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = too-many-statements, protected-access, unused-variable

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from copy import deepcopy
import pytest

from zm.error import *
from zm.constants import *
from zm.pathutils import unfoldPath
from zm.buildconf.processing import Config as BuildConfig
from tests.common import asRealConf, randomstr

joinpath = os.path.join

@pytest.mark.usefixtures("unsetEnviron")
class TestSuite(object):

    def testInit(self, testingBuildConf):
        buildconf = testingBuildConf
        conf = asRealConf(buildconf)
        bconf = BuildConfig(conf)
        assert bconf.selectedBuildType == ''
        assert bconf._conf == conf
        assert bconf.projectName == buildconf.project.name
        assert bconf.projectVersion == buildconf.project.version

    def testDefaultBuildType(self, testingBuildConf):
        buildconf = testingBuildConf

        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == ''

        buildconf.buildtypes.mybuildtype = {}

        # CASE: buildconf.buildtypes.default is absent but one buildtype is defined
        buildconf = deepcopy(testingBuildConf)
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'mybuildtype'

        # and second buildtype
        buildconf.buildtypes.abc = {}

        # CASE: buildconf.buildtypes.default as a string
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.default = 'mybuildtype'
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.defaultBuildType == 'mybuildtype'

        # CASE: buildconf.buildtypes.default as a dict
        for name in ('_', 'no-match', PLATFORM):
            buildconf = deepcopy(testingBuildConf)
            buildconf.buildtypes.default = { name: 'mybuildtype' }
            bconf = BuildConfig(asRealConf(buildconf))
            assert bconf.defaultBuildType == 'mybuildtype'

        # CASE: buildconf.buildtypes.default is not valid
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.default = 'mybuildtype2'
        with pytest.raises(ZenMakeError):
            bconf = BuildConfig(asRealConf(buildconf))
            _ = bconf.defaultBuildType

        for name in ('_', 'no-match', PLATFORM):
            buildconf = deepcopy(testingBuildConf)
            buildconf.buildtypes.default = { name: 'mybuildtype2' }
            with pytest.raises(ZenMakeError):
                bconf = BuildConfig(asRealConf(buildconf))
                _ = bconf.defaultBuildType

    def testSelectedBuildType(self, testingBuildConf):
        buildconf = testingBuildConf
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.selectedBuildType == 'mybuildtype'

        clivars = { 'buildtype': 'mybtype' }
        bconf = BuildConfig(asRealConf(buildconf), clivars)
        assert bconf.selectedBuildType == 'mybtype'

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

    def testSupportedBuildTypesByfilter(self, testingBuildConf):

        buildconf = testingBuildConf
        buildconf.buildtypes.default = 'b1'

        # CASE: no buildtypes in buildconf.buildtypes and global
        # buildtypes in byfilter
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2' } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2' } },
            { 'for' : { 'buildtype' : ['b3', 'b2'] } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3' ])

        # CASE: no buildtypes in buildconf.buildtypes and platform
        # buildtypes in byfilter
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.default = 'b2'
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b4 b2', 'platform' : PLATFORM } },
            { 'for' : { 'buildtype' : 'b5 b6', 'platform' : PLATFORM } }
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b4', 'b2', 'b5', 'b6' ])

        # CASE: no buildtypes in buildconf.buildtypes and global/platform
        # buildtypes in byfilter
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3' ])
        buildconf.buildtypes.default = 'b2'
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b2', 'b3' ])

        # CASE: buildtypes in buildconf.buildtypes and global/platform
        # buildtypes in byfilter
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.gb1 = {}
        buildconf.buildtypes.default = 'b2'
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2' } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'gb1', 'b1', 'b2' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'gb1', 'b1', 'b2' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1 b2', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b3 b2', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'gb1', 'b2', 'b3' ])

        # CASE: buildtypes in buildconf.buildtypes and buildtypes in byfilter
        buildconf = deepcopy(testingBuildConf)
        buildconf.buildtypes.b1 = {}
        buildconf.buildtypes.b2 = {}
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b3 b4' } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3', 'b4' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b3 b4', 'platform' : PLATFORM } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3', 'b4' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b5 b3', 'platform' : PLATFORM + randomstr() } },
            { 'for' : { 'buildtype' : 'b4 b3', } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2', 'b3', 'b4' ])
        buildconf.byfilter = [
            { 'for' : { 'buildtype' : 'b1' } },
        ]
        self._checkSupportedBuildTypes(buildconf, [ 'b1', 'b2' ])

    def _checkTasks(self, buildconf, buildtype, expected):
        bconf = BuildConfig(asRealConf(buildconf), clivars = {'buildtype': buildtype})

        expected = expected.copy()
        for task in expected:
            taskParams = expected[task]
            taskParams['$startdir'] = '.'
            taskParams['$bconf'] = bconf
            for name, value in taskParams.items():
                taskParams[name] = value

        assert bconf.tasks == expected
        # to force covering of cache
        assert bconf.tasks == expected

    def testTasks(self, testingBuildConf):
        buildconf = testingBuildConf

        # CASE: invalid use
        bconf = BuildConfig(asRealConf(buildconf))
        empty = bconf.tasks
        assert empty is not None and not empty

        buildconf.buildtypes.default = 'mybuildtype'
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}
        buildtype = 'mybuildtype'

        # CASE: just empty buildconf.tasks
        buildconf = deepcopy(testingBuildConf)
        bconf = BuildConfig(asRealConf(buildconf), clivars = {'buildtype': buildtype})
        assert bconf.tasks == {}
        # this assert just for in case
        assert bconf.selectedBuildType == 'mybuildtype'

        # CASE: just some buildconf.tasks, nothing else
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.name = 'test1'
        buildconf.tasks.test2.name = 'test2'
        buildconf.tasks.test1.param1 = '1'
        buildconf.tasks.test2.param2 = '2'
        self._checkTasks(buildconf, buildtype, buildconf.tasks)

        # CASE: some buildconf.tasks and buildconf.buildtypes
        # with non-empty selected buildtype
        # buildtype 'mybuildtype' should be selected at this moment
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.name = 'test1'
        buildconf.tasks.test2.name = 'test2'
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
        buildconf.tasks.test1.name = 'test1'
        buildconf.tasks.test2.name = 'test2'
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

    def testTasksByfilter(self, testingBuildConf):

        buildtype = 'mybt'
        testingBuildConf.buildtypes.mybt = {}
        testingBuildConf.buildtypes.default = 'mybt'
        baseByfilter = [
            { 'for' : { 'buildtype' : 'mybt' }  },
        ]

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.byfilter
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = baseByfilter + [
            { 'for' : { 'task' : 't1' }, 'set' : { 'param1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'param2' : '2' } },
        ]
        expected = {
            't1': {'name' : 't1', 'param1': '1'},
            't2': {'name' : 't2', 'param2': '2'}
        }
        self._checkTasks(buildconf, buildtype, expected)

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.byfilter
        # with non-empty selected buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = baseByfilter + [
            {
                'for' : { 'task' : 't1', 'buildtype' : 'b1 b2', },
                'set' : { 'param1' : '1' }
            },
            {
                'for' : { 'task' : 't2', 'buildtype' : 'mybt', },
                'set' : { 'param2' : '2' }
            },
        ]
        self._checkTasks(buildconf, buildtype, {
            't1': {'name' : 't1'},
            't2': {'name' : 't2', 'param2': '2'}
        })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.byfilter
        # Applying for all tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = baseByfilter + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p1' : '1' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p2' : '2' } },
        ]
        self._checkTasks(buildconf, buildtype, {
            't1': {'name' : 't1', 'p1': '1', 'p3': '3'},
            't2': {'name' : 't2', 'p2': '2', 'p3': '3'},
        })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.byfilter
        # Merging/replacing params in tasks
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = baseByfilter + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p1' : '1', 'p2' : '2' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p2' : '22' } },
            { 'for' : { 'task' : 't1' }, 'set' : { 'p4' : '4', 'p2' : '-2-' } },
        ]
        self._checkTasks(buildconf, buildtype, {
            't1': {'name' : 't1', 'p1': '1', 'p3': '3', 'p2' : '-2-', 'p4' : '4'},
            't2': {'name' : 't2', 'p2': '22', 'p3': '3'},
        })

        # CASE: no tasks in buildconf.tasks, some tasks in buildconf.byfilter
        # with non-empty platform
        buildconf = deepcopy(testingBuildConf)
        buildconf.byfilter = baseByfilter + [
            {
                'for' : { 'task' : 't1', },
                'set' : { 'p1' : '1' }
            },
            {
                'for' : { 'task' : 't2', 'platform' : PLATFORM, },
                'set' : { 'p2' : '2' }
            },
        ]
        expected = {
            't1': {'name' : 't1', 'p1': '1'},
            't2': {'name' : 't2', 'p2': '2'}
        }
        self._checkTasks(buildconf, buildtype, expected)
        buildconf.byfilter = baseByfilter + [
            {
                'for' : { 'task' : 't1', 'platform' : PLATFORM },
                'set' : { 'p1' : '1' }
            },
            {
                'for' : { 'task' : 't2', 'platform' : PLATFORM + randomstr(), },
                'set' : { 'p2' : '2' }
            },
        ]
        expected = {
            't1': {'name' : 't1', 'p1': '1'}, 't2': { 'name' : 't2' }
        }
        self._checkTasks(buildconf, buildtype, expected)

        # CASE: some tasks in buildconf.tasks, some tasks in buildconf.byfilter
        # complex merging
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.t1.p1 = '1'
        buildconf.tasks.t2.p2 = '2'
        buildconf.tasks.t2.p3 = '2'
        buildconf.byfilter = baseByfilter + [
            { 'for' : {}, 'set' : { 'p3' : '3' } },
            { 'for' : { 'task' : 't3' }, 'set' : { 'p1' : '1', 'p2' : '2' } },
            { 'for' : { 'task' : 't2' }, 'set' : { 'p1' : '11' } },
            { 'for' : { 'task' : 't4' }, 'set' : { 'p5' : '1', 'p6' : '2' } },
        ]
        self._checkTasks(buildconf, buildtype, {
            't1': {'name' : 't1', 'p1': '1', 'p3': '3'},
            't2': {'name' : 't2', 'p1': '11', 'p2': '2', 'p3': '3'},
            't3': {'name' : 't3', 'p1': '1', 'p2': '2', 'p3': '3'},
            't4': {'name' : 't4', 'p5': '1', 'p6': '2', 'p3': '3'},
        })

    def testCustomToolchains(self, testingBuildConf, capsys):
        buildconf = testingBuildConf

        buildconf.buildtypes['debug-gxx'] = {}
        buildconf.buildtypes.default = 'debug-gxx'

        # CASE: no custom toolchains
        buildconf = deepcopy(testingBuildConf)
        bconf = BuildConfig(asRealConf(buildconf))
        assert bconf.customToolchains == {}

        # CASE: one custom toolchain with fake path
        buildconf = deepcopy(testingBuildConf)
        buildconf.toolchains = {
            'something' : {
                'kind': 'auto-c++',
                'CXX': joinpath('path', 'to', 'toolchain')
            },
        }
        bconf = BuildConfig(asRealConf(buildconf))
        confPaths = bconf.confPaths
        expected = deepcopy(buildconf.toolchains)
        expected['something']['vars'] = {
            'CXX' : [unfoldPath(confPaths.startdir,
                                     buildconf.toolchains['something']['CXX'])]
        }
        del expected['something']['CXX']
        assert bconf.customToolchains == expected
        captured = capsys.readouterr()
        assert "doesn't exist" in captured.err
        # to force covering of cache
        assert bconf.customToolchains == expected
