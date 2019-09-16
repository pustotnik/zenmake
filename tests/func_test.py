# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import re
import subprocess
import shutil
from collections import defaultdict

import pytest
from waflib import Build
from waflib.ConfigSet import ConfigSet
import tests.common as cmn
from zm import starter
from zm import pyutils, assist, cli, utils, zipapp
from zm.buildconf import loader as bconfloader
from zm.buildconf.handler import BuildConfHandler
from zm.constants import ZENMAKE_COMMON_FILENAME, PLATFORM, APPNAME

joinpath = os.path.join
ZM_BIN = cmn.ZENMAKE_DIR # it's a dir but it contains __main__.py
PYTHON_EXE = sys.executable if sys.executable else 'python'

CUSTOM_TOOLCHAIN_PRJDIR = joinpath('cpp', '005-custom-toolchain')
COMPLEX_UNITTEST_PRJDIR = joinpath('cpp', '009-complex-unittest')

def collectProjectDirs():
    result = []
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.py' not in filenames and 'buildconf.yaml' not in filenames:
            continue
        prjdir = os.path.relpath(dirpath, cmn.TEST_PROJECTS_DIR)
        if prjdir == CUSTOM_TOOLCHAIN_PRJDIR and cmn.PLATFORM == 'windows':
            print('We ignore tests for %r on windows' % prjdir)
            continue
        result.append(prjdir)
    result.sort()
    return result

_zmExes = {}

def getZmExecutables():

    tmpdir = cmn.SHARED_TMP_DIR
    zipAppFile = joinpath(tmpdir, APPNAME)
    if _zmExes:
        return _zmExes.keys()

    zipAppFile = zipapp.make(tmpdir)

    _zmExes['normal'] = [PYTHON_EXE, ZM_BIN]

    # On Windows 10 .pyz can be used as is because there is
    # a launcher (python.exe) that assosiated with this file extension in
    # the system. But module subprocess can not do it. So it needs to
    # specify python executable.
    # Also on all platforms to ensure that selected version of python is used
    # we should specify python executable. Otherwise default system python
    # will be used.
    _zmExes['zipapp'] = [PYTHON_EXE, zipAppFile]
    return _zmExes.keys()

def runZm(self, cmdline, env = None):

    cwd = self.cwd
    zmExe = self.zmExe if hasattr(self, 'zmExe') else [PYTHON_EXE, ZM_BIN]
    cmdLine = zmExe + utils.toList(cmdline)

    timeout = 60 * 15
    _env = os.environ.copy()
    if env:
        _env.update(env)
    proc = subprocess.Popen(cmdLine, stdout = subprocess.PIPE,
                        stderr = subprocess.STDOUT, cwd = cwd,
                        env = _env, universal_newlines = True)
    kw = {}
    if pyutils.PY3:
        kw['timeout'] = timeout
    stdout, stderr = proc.communicate(**kw)

    self.zm = dict(
        stdout = stdout,
        stderr = stderr,
        exitcode = proc.returncode,
    )
    return proc.returncode, stdout, stderr

def printOutputs(self):
    zmInfo = getattr(self, 'zm', None)
    if not zmInfo:
        return
    for param in ('stdout', 'stderr'):
        out = zmInfo.get(param, None)
        if out:
            print('\n' + out)

def setupTest(self, request, tmpdir):

    #testName = request.node.originalname
    #if not testName:
    #    testName = request.node.name

    #projectDirName = request.param
    projectDirName = 'prj'

    if PLATFORM == 'windows':
        # On windows with pytest it's got too long path
        projectDirName = '_' # shortest name
        tmpdirForTests = cmn.SHARED_TMP_DIR
        tmptestDir = joinpath(tmpdirForTests, projectDirName)
        shutil.rmtree(tmptestDir, ignore_errors = True)
    else:
        tmptestDir = joinpath(str(tmpdir.realpath()), projectDirName)

    def copytreeIgnore(src, names):
        # don't copy build dir/files
        if ZENMAKE_COMMON_FILENAME in names:
            return names
        return ['build']

    currentPrjDir = joinpath(cmn.TEST_PROJECTS_DIR, request.param)
    prjBuildDir = joinpath(currentPrjDir, 'build')
    if os.path.exists(prjBuildDir):
        prjBuildDir = os.path.realpath(prjBuildDir)
        if os.path.isdir(prjBuildDir):
            shutil.rmtree(prjBuildDir, ignore_errors = True)
    shutil.copytree(currentPrjDir, tmptestDir, ignore = copytreeIgnore)

    self.cwd = tmptestDir
    projectConf = bconfloader.load('buildconf', self.cwd)
    self.confHandler = BuildConfHandler(projectConf)
    self.confPaths = self.confHandler.confPaths


@pytest.mark.usefixtures("unsetEnviron")
class TestBase(object):

    def _runZm(self, cmdline):
        return runZm(self, utils.toList(cmdline) + ['-v'])

    def _checkBuildResults(self, cmdLine, resultExists):
        # checks for target files
        cmdLine = list(cmdLine)
        cmdLine.insert(0, APPNAME)
        cmd, _ = starter.handleCLI(self.confHandler, cmdLine, True)
        self.confHandler.handleCmdLineArgs(cmd)
        buildtype = self.confHandler.selectedBuildType

        checkingFeatures = set((
            'cprogram', 'cxxprogram', 'cstlib',
            'cxxstlib', 'cshlib', 'cxxshlib',
        ))

        for taskName, taskParams in self.confHandler.tasks.items():
            taskVariant = assist.makeTaskVariantName(buildtype, taskName)
            cacheConfFile = assist.makeCacheConfFileName(
                                            self.confPaths.zmcachedir, taskVariant)
            env = ConfigSet(cacheConfFile)
            target = taskParams.get('target', taskName)
            executable = False
            fileNamePattern = '%s'
            features = set(utils.toList(taskParams.get('features', '')))
            if 'test' in features:
                # ignore test tasks
                continue
            if not [ x for x in features if x in checkingFeatures ]:
                # check only with features from checkingFeatures
                continue
            for feature in features:
                # find pattern via brute force :)
                key = feature + '_PATTERN'
                if key not in env:
                    continue
                fileNamePattern = env[key]
                executable = feature.endswith('program')

            targetpath = joinpath(self.confPaths.buildout, buildtype,
                                  fileNamePattern % target)
            assert os.path.exists(targetpath) == resultExists
            assert os.path.isfile(targetpath) == resultExists
            if resultExists and executable:
                assert os.access(targetpath, os.X_OK)

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    @pytest.fixture(params = collectProjectDirs())
    def allprojects(self, request, tmpdir):

        def teardown():
            if request.node.rep_call.failed:
                printOutputs(self)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    @pytest.fixture(params = [CUSTOM_TOOLCHAIN_PRJDIR])
    def customtoolchains(self, request, tmpdir):
        setupTest(self, request, tmpdir)

    def testConfigureAndBuild(self, allprojects):

        cmdLine = ['configure']
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, False)
        assert os.path.isfile(self.confPaths.wafcachefile)
        assert os.path.isfile(self.confPaths.zmcmnfile)

        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, True)

    def testBuild(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, True)

    def testBuildAndBuild(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, True)

        # simple rebuild
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, True)

    def testBuildAndClean(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, True)

        # clean
        cmdLine = ['clean']
        assert self._runZm(cmdLine)[0] == 0
        assert os.path.isdir(self.confPaths.buildroot)
        assert os.path.isdir(self.confPaths.buildout)
        assert os.path.isfile(self.confPaths.wafcachefile)
        assert os.path.isfile(self.confPaths.zmcmnfile)
        self._checkBuildResults(cmdLine, False)

    def testBuildAndDistclean(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        self._checkBuildResults(cmdLine, True)

        # distclean
        assert os.path.isdir(self.confPaths.buildroot)
        cmdLine = ['distclean']
        assert self._runZm(cmdLine)[0] == 0
        assert not os.path.exists(self.confPaths.buildroot)

    @pytest.mark.skipif(cmn.PLATFORM == 'windows',
                        reason = 'I have no useful windows installation for tests')
    def testCustomToolchain(self, customtoolchains):

        cmdLine = ['build']
        returncode, stdout, stderr =  self._runZm(cmdLine)
        assert returncode == 0
        self._checkBuildResults(cmdLine, True)

        cmd, _ = starter.handleCLI(self.confHandler, [APPNAME] + cmdLine, True)
        self.confHandler.handleCmdLineArgs(cmd)

        for taskName, taskParams in self.confHandler.tasks.items():
            toolchain = taskParams.get('toolchain', None)
            assert toolchain is not None
            if not toolchain.startswith('custom-'):
                continue
            emukind = toolchain[7:]
            assert emukind
            checkmsg = '%s wrapper for custom toolchain test' % emukind
            assert checkmsg in stdout

def gatherEventsFromOutput(output):

    CMD_NAMES = ('build', 'test')

    events = {}
    cmdEvents = []
    cmdOutput = []
    taskRealCount = 0
    taskMaxCount = 0
    cmdIndexes = defaultdict(dict)
    sep = os.path.sep

    def findCmdEnd(line):
        for cmdName in CMD_NAMES:
            m = re.match(r"'%s'\s+finished" % cmdName, line)
            if m:
                return cmdName
        return None

    for line in output.splitlines():
        cmdName = findCmdEnd(line)
        if cmdName:
            events[cmdName] = dict(
                events = cmdEvents,
                indexes = cmdIndexes,
                output = cmdOutput,
                taskRealCount = taskRealCount,
                taskMaxCount = taskMaxCount,
            )
            cmdEvents = []
            cmdOutput = []
            taskRealCount = 0
            taskMaxCount = 0
            cmdIndexes = defaultdict(dict)
            continue

        isWafTaskStarting = False
        m = re.match(r"^\s*\[\s*\d+/(\d+)\s*\]\s+.+", line)
        if m:
            taskRealCount += 1
            taskMaxCount = int(m.group(1))
            isWafTaskStarting = True

        m = re.match(r"^\s*\[\s*\d+/\d+\s*\]\s+Linking\s+.+\%s(lib)?([\w\-\s]+)" % sep, line)
        if m:
            task = m.group(2)
            cmdEvents.append(['linking', task])
            cmdIndexes['linking'][task] = len(cmdEvents) - 1
            continue

        m = re.match(r"^\s*\[\s*\d+/\d+\s*\]\s+Running\s+command\s+.*?\'([\w\s.\-]+)\'$", line)
        if m:
            task = m.group(1)
            cmdEvents.append(['running', task])
            cmdIndexes['running'][task] = len(cmdEvents) - 1
            continue

        m = re.match(r"\s*Running\s+test:\s+\'([\w\s.\-]+)\'$", line)
        if m:
            task = m.group(1)
            cmdEvents.append(['running', task])
            cmdIndexes['running'][task] = len(cmdEvents) - 1
            continue

        terminators = [r"^Waf:\s+"]
        if isWafTaskStarting or any([ bool(re.match(expr, line)) for expr in terminators ]):
            continue

        cmdOutput.append(line)

    if cmdEvents:
        events['unknown'] = cmdEvents

    return events

def checkMsgInOutput(msg, output, count = None):
    if isinstance(output, list):
        output = '\n'.join(output)

    if not count:
        assert msg in output
    else:
        assert output.count(msg) == count

@pytest.mark.usefixtures("unsetEnviron")
class TestFeatureRunCmd(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    @pytest.fixture(params = [COMPLEX_UNITTEST_PRJDIR])
    def projects(self, request, tmpdir):

        def teardown():
            if request.node.rep_call.failed:
                printOutputs(self)

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

        # check cmd output and repeat
        checkMsgInOutput(r'This is runcmd in task "shlib"', output, 1)
        checkMsgInOutput(r'This is runcmd in task "complex"', output, 1)
        checkMsgInOutput(r'say hello', output, 2)
        checkMsgInOutput(r'test from a python script', output, 1)

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
        assert self.zm['exitcode'] != 0

@pytest.mark.usefixtures("unsetEnviron")
class TestFeatureTest(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    @pytest.fixture(params = [COMPLEX_UNITTEST_PRJDIR])
    def projects(self, request, tmpdir):

        def teardown():
            if request.node.rep_call.failed:
                printOutputs(self)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def _runAndGather(self, cmdLine, exitSuccess):

        returncode, stdout, stderr = runZm(self, cmdLine)
        events = gatherEventsFromOutput(stdout)
        if exitSuccess:
            assert returncode == 0
            assert not stderr
            assert 'unknown' not in events
        else:
            assert returncode != 0

        return events

    def _checkFeatureBTNoRTNone(self, cmdLine):
        events = self._runAndGather(cmdLine, True)
        indexes = events['build']['indexes']

        assert len(indexes['linking']) == 4
        assert events['build']['taskRealCount'] == 14
        assert events['build']['taskMaxCount'] == 14

    def _checkFeatureBTYesRTNone(self, cmdLine):
        events = self._runAndGather(cmdLine, True)
        indexes = events['build']['indexes']

        assert len(indexes['linking']) == 8
        assert events['build']['taskRealCount'] == 22
        assert events['build']['taskMaxCount'] == 22

    def _checkFeatureRTAllVariants(self, cmdLines):

        if cmdLines[0]:
            events = self._runAndGather(cmdLines[0], False)
            indexes = events['build']['indexes']

            assert len(indexes['linking']) == 4
            assert events['build']['taskRealCount'] == 14
            assert events['build']['taskMaxCount'] == 14

        noFirstStep = not cmdLines[0]

        if cmdLines[1]:
            events = self._runAndGather(cmdLines[1], True)
            indexes = events['build']['indexes']

            assert len(indexes['linking']) == 8 if noFirstStep else 4
            assert events['build']['taskRealCount'] == 22 if noFirstStep else 8
            assert events['build']['taskMaxCount'] == 22

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
                break;

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
        cmdLine = ['build', '--build-tests', 'no', '--run-tests', 'none']
        self._checkFeatureBTNoRTNone(cmdLine)

    def testCmdBuildBTYesRTNone(self, projects):
        cmdLine = ['build', '--build-tests', 'yes', '--run-tests', 'none']
        self._checkFeatureBTYesRTNone(cmdLine)

    def testCmdBuildRTAllVariants(self, projects):

        self._checkFeatureRTAllVariants([
            ['build', '--build-tests', 'no', '--run-tests', 'all'],
            ['build', '--build-tests', 'yes', '--run-tests', 'all'],
            ['build', '--build-tests', 'yes', '--run-tests', 'on-changes'],
        ])

    def testCmdTest(self, projects):
        self._checkFeatureRTAllVariants([ None, ['test'], None ])

    def testCmdTestBTNoRTNone(self, projects):
        cmdLine = ['test', '--build-tests', 'no', '--run-tests', 'none']
        self._checkFeatureBTNoRTNone(cmdLine)

    def testCmdTestBTYesRTNone(self, projects):
        cmdLine = ['test', '--build-tests', 'yes', '--run-tests', 'none']
        self._checkFeatureBTYesRTNone(cmdLine)

    def testCmdTestRTAllVariants(self, projects):

        self._checkFeatureRTAllVariants([
            ['test', '--build-tests', 'no', '--run-tests', 'all'],
            ['test', '--build-tests', 'yes', '--run-tests', 'all'],
            ['test', '--build-tests', 'yes', '--run-tests', 'on-changes'],
        ])
