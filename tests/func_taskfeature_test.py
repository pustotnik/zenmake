# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = unused-argument, no-member, attribute-defined-outside-init
# pylint: disable = too-many-lines, too-many-branches, too-many-statements

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import pytest

from tests.func_utils import *

COMPLEX_UNITTEST_PRJDIR = joinpath('cpp', '09-complex-unittest')

@pytest.mark.usefixtures("unsetEnviron")
class TestFeatureRunCmd(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = [COMPLEX_UNITTEST_PRJDIR])
    def projects(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def testBasis(self, projects):

        cmdLine = ['build']
        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0
        events = gatherEventsFromOutput(stdout)
        assert 'unknown' not in events
        indexes = events['build']['indexes']
        output = events['build']['output']

        # check order
        assert indexes['running']['shlib'] > indexes['linking']['shlib']
        assert indexes['running']['complex'] > indexes['linking']['complex']
        assert indexes['running']['echo'] > indexes['linking']['shlibmain']
        assert indexes['running']['test.py'] > indexes['linking']['shlibmain']
        assert indexes['compiling']['shlibmain/util.cpp'] > indexes['running']['ls']

        # check cmd output and repeat
        checkMsgInOutput(r'This is runcmd in task "shlib"', output, 1)
        checkMsgInOutput(r'This is runcmd in task "complex"', output, 1)
        checkMsgInOutput(r'say hello', output, 2)
        checkMsgInOutput(r'test from a python script', output, 1)
        checkMsgInOutput(r'somefunc: buildtype =', output, 1)

        #check env var (see buildconf)
        checkMsgInOutput(r'JUST_ENV_VAR = qwerty', output, 1)

        # cwd is checking by calling test.py - it will break
        # running with incorrect cwd

        # check 'shell': check result of ls/dir command on project dir
        checkMsgInOutput('buildconf.py', output)
        checkMsgInOutput('shlibmain', output)

        #check running of a script with a space in its name
        checkMsgInOutput("it works", output)

    def testRunFailed(self, projects):
        cmdLine = ['build']
        env = { 'RUN_FAILED': '1' }
        runZm(self, cmdLine, env)
        assert self.zmresult.exitcode != 0

@pytest.mark.usefixtures("unsetEnviron")
class TestFeatureTest(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = [COMPLEX_UNITTEST_PRJDIR])
    def projects(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def _runAndGather(self, cmdLine, exitSuccess):

        exitcode, stdout, stderr = runZm(self, cmdLine)
        events = gatherEventsFromOutput(stdout)
        if exitSuccess:
            assert exitcode == 0
            assert not stderr
            assert 'unknown' not in events
        else:
            assert exitcode != 0

        return events

    def _checkFeatureBTNoRTNone(self, cmdLine):
        events = self._runAndGather(cmdLine, True)
        indexes = events['build']['indexes']

        assert len(indexes['linking']) == 4
        assert events['build']['taskRealCount'] == 15
        assert events['build']['taskMaxCount'] == 15

    def _checkFeatureBTYesRTNone(self, cmdLine):
        events = self._runAndGather(cmdLine, True)
        indexes = events['build']['indexes']

        assert len(indexes['linking']) == 8
        assert events['build']['taskRealCount'] == 23
        assert events['build']['taskMaxCount'] == 23

    def _checkFeatureRTAllVariants(self, cmdLines):

        if cmdLines[0]:
            events = self._runAndGather(cmdLines[0], True)
            indexes = events['build']['indexes']

            assert len(indexes['linking']) == 4
            assert events['build']['taskRealCount'] == 15
            assert events['build']['taskMaxCount'] == 15

        noFirstStep = not cmdLines[0]

        if cmdLines[1]:
            events = self._runAndGather(cmdLines[1], True)
            indexes = events['build']['indexes']

            assert len(indexes['linking']) == 8 if noFirstStep else 4
            assert events['build']['taskRealCount'] == 23 if noFirstStep else 8
            assert events['build']['taskMaxCount'] == 23

            indexes = events['test']['indexes']
            runningTasks = indexes['running']
            assert len(runningTasks) == 4
            assert runningTasks['test from script'] > runningTasks['stlib-test']
            assert runningTasks['test from script'] > runningTasks['shlib-test']
            assert runningTasks['test from script'] > runningTasks['shlibmain-test']
            assert runningTasks['shlibmain-test'] > runningTasks['stlib-test']
            assert runningTasks['shlibmain-test'] > runningTasks['shlib-test']

            output = events['test']['output']
            checkMsgInOutput('Tests of stlib ...', output, 1)
            checkMsgInOutput('Tests of shlib ...', output, 2)
            checkMsgInOutput("env var 'AZ' = 111", output, 2)
            checkMsgInOutput('Tests of shlibmain ...', output, 1)
            checkMsgInOutput('test from a python script', output, 1)

        ### on changes
        if not cmdLines[2]:
            return

        fpath = joinpath(self.cwd, 'stlib', 'util.cpp')
        lines = []
        with open(fpath, 'r') as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if not ('cout' in line and 'calcSum' in line):
                    continue
                lines.insert(i + 1, 'std::cout << "Test was changed" << std::endl;\n')
                break

        with open(fpath, 'w') as file:
            file.writelines(lines)

        events = self._runAndGather(cmdLines[2], True)
        indexes = events['test']['indexes']
        runningTasks = indexes['running']

        assert len(runningTasks) == 2
        assert 'stlib-test' in runningTasks
        assert 'shlibmain-test' in runningTasks
        assert runningTasks['shlibmain-test'] > runningTasks['stlib-test']
        output = events['test']['output']
        checkMsgInOutput('Tests of stlib ...', output, 1)
        checkMsgInOutput('Tests of shlibmain ...', output, 1)

    def testCmdBuildBTNoRTNone(self, projects):
        cmdLine = ['build', '--with-tests', 'no', '--run-tests', 'none']
        self._checkFeatureBTNoRTNone(cmdLine)

    def testCmdBuildBTYesRTNone(self, projects):
        cmdLine = ['build', '--with-tests', 'yes', '--run-tests', 'none']
        self._checkFeatureBTYesRTNone(cmdLine)

        # clean
        cmdLine = ['clean']
        assert runZm(self, cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, False, True)
        assert isdir(self.confPaths.buildroot)
        assert isdir(self.confPaths.buildout)
        assert isfile(self.confPaths.wafcachefile)
        assert isfile(self.confPaths.zmmetafile)

    def testCmdBuildRTAllVariants(self, projects):

        self._checkFeatureRTAllVariants([
            ['build', '--with-tests', 'no', '--run-tests', 'all'],
            ['build', '--with-tests', 'yes', '--run-tests', 'all'],
            ['build', '--with-tests', 'yes', '--run-tests', 'on-changes'],
        ])

    def testCmdTest(self, projects):
        self._checkFeatureRTAllVariants([ None, ['test'], None ])

    def testCmdTestBTNoRTNone(self, projects):
        cmdLine = ['test', '--with-tests', 'no', '--run-tests', 'none']
        self._checkFeatureBTNoRTNone(cmdLine)

    def testCmdTestBTYesRTNone(self, projects):
        cmdLine = ['test', '--with-tests', 'yes', '--run-tests', 'none']
        self._checkFeatureBTYesRTNone(cmdLine)

        # clean
        cmdLine = ['clean']
        assert runZm(self, cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, False, True)
        assert isdir(self.confPaths.buildroot)
        assert isdir(self.confPaths.buildout)
        assert isfile(self.confPaths.wafcachefile)
        assert isfile(self.confPaths.zmmetafile)

    def testCmdTestRTAllVariants(self, projects):

        self._checkFeatureRTAllVariants([
            ['test', '--with-tests', 'no', '--run-tests', 'all'],
            ['test', '--with-tests', 'yes', '--run-tests', 'all'],
            ['test', '--with-tests', 'yes', '--run-tests', 'on-changes'],
        ])
