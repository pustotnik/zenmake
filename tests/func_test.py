# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import io
import re
import subprocess
import shutil
import platform as _platform
from collections import defaultdict
from copy import copy, deepcopy
from zipfile import ZipFile, is_zipfile as iszip

import pytest
from waflib import Build, Context
from waflib.ConfigSet import ConfigSet
import tests.common as cmn
from zm import starter
from zm import pyutils, assist, cli, utils, zipapp, version
from zm.autodict import AutoDict
from zm.buildconf import loader as bconfloader
from zm.buildconf.handler import ConfHandler as BuildConfHandler
from zm.constants import ZENMAKE_CMN_CFGSET_FILENAME, PLATFORM, APPNAME
from zm.constants import TASK_WAF_MAIN_FEATURES
from zm.toolchains import CompilersInfo
from zm.buildconf.scheme import KNOWN_CONF_PARAM_NAMES

joinpath = os.path.join
ZM_BIN = cmn.ZENMAKE_DIR # it's a dir but it contains __main__.py
PYTHON_EXE = sys.executable if sys.executable else 'python'
PYTHON_VER = _platform.python_version()

CUSTOM_TOOLCHAIN_PRJDIR = joinpath('cpp', '05-custom-toolchain')
COMPLEX_UNITTEST_PRJDIR = joinpath('cpp', '09-complex-unittest')
FORINSTALL_PRJDIRS = [joinpath('cpp', '04-complex'), joinpath('cpp', '09-complex-unittest')]

TEST_CONDITIONS = {
    CUSTOM_TOOLCHAIN_PRJDIR: dict( os = ['linux', 'darwin'], ),
    joinpath('asm', '01-simple-gas') : dict( os = ['linux']),
    joinpath('asm', '02-simple-nasm') :
        dict( os = ['linux'], py = ['2.7', '3.6', '3.7', '3.8']),
}

def collectProjectDirs():
    for path in TEST_CONDITIONS:
        path = joinpath(cmn.TEST_PROJECTS_DIR, path)
        assert os.path.isdir(path)

    result = []
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.py' not in filenames and 'buildconf.yaml' not in filenames:
            continue
        prjdir = os.path.relpath(dirpath, cmn.TEST_PROJECTS_DIR)
        condition = TEST_CONDITIONS.get(prjdir, None)
        if condition:
            destos =  condition.get('os')
            if destos and PLATFORM not in destos:
                print('We ignore tests for %r on %r' % (prjdir, PLATFORM))
                continue
            py = condition.get('py')
            if py and not any(PYTHON_VER.startswith(x) for x in py):
                print('We ignore tests for %r on python %r' % (prjdir, PYTHON_VER))
                continue
        result.append(prjdir)
    result.sort()
    return result

_zmExes = {}

def getZmExecutables():

    tmpdir = cmn.SHARED_TMP_DIR
    zipAppFile = joinpath(tmpdir, zipapp.ZIPAPP_NAME)
    if _zmExes:
        return _zmExes.keys()

    _zmExes['normal'] = [PYTHON_EXE, ZM_BIN]

    cmd = _zmExes['normal'] + ['zipapp', '--destdir', tmpdir]
    devnull = open(os.devnull, 'w')
    subprocess.call(cmd, stdout = devnull)
    assert os.path.isfile(zipAppFile)

    # On Windows 10 files *.pyz can be used as is because there is
    # a launcher (python.exe) that assosiated with this file extension in
    # the system. But python module subprocess cannot do it. So it needs to
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
        # On windows with pytest it gets too long path
        projectDirName = '_' # shortest name
        tmpdirForTests = cmn.SHARED_TMP_DIR
        tmptestDir = joinpath(tmpdirForTests, projectDirName)
        shutil.rmtree(tmptestDir, ignore_errors = True)
    else:
        tmptestDir = joinpath(str(tmpdir.realpath()), projectDirName)

    def copytreeIgnore(src, names):
        # don't copy build dir/files
        if ZENMAKE_CMN_CFGSET_FILENAME in names:
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
    self.projectConf = bconfloader.load(dirpath = self.cwd)

def processConfHandlerWithCLI(testSuit, cmdLine):
    cmdLine = list(cmdLine)
    cmdLine.insert(0, APPNAME)

    cmd, _ = starter.handleCLI(cmdLine, True, None)
    cliBuildRoot = cmd.args.get('buildroot', None)

    testSuit.confHandler = BuildConfHandler(testSuit.projectConf, cliBuildRoot)
    testSuit.confPaths = testSuit.confHandler.confPaths

    cmd, _ = starter.handleCLI(cmdLine, False, testSuit.confHandler)
    testSuit.confHandler.applyBuildType(cmd.args.buildtype)

def getTaskEnv(testSuit, taskName):
    buildtype = testSuit.confHandler.selectedBuildType
    taskVariant = assist.makeTaskVariantName(buildtype, taskName)
    cacheConfFile = assist.makeCacheConfFileName(
                                    testSuit.confPaths.zmcachedir, taskVariant)
    env = ConfigSet(cacheConfFile)
    return env

def getTargetPattern(testSuit, taskName, features):
    executable = False
    fileNamePattern = '%s'
    env = getTaskEnv(testSuit, taskName)
    for feature in features:
        # find pattern via brute force :)
        key = feature + '_PATTERN'
        if key not in env:
            continue
        fileNamePattern = env[key]
        executable = feature.endswith('program')

    return fileNamePattern, executable

def handleTaskFeatures(testSuit, taskParams):
    assist.detectConfTaskFeatures(taskParams)
    if 'source' in taskParams:
        confPaths = testSuit.confPaths
        srcDir = os.path.relpath(confPaths.srcroot, confPaths.buildconfdir)
        ctx = Context.Context(run_dir = testSuit.cwd)
        srcDirNode = ctx.path.find_dir(srcDir)
        taskParams['source'] = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assist.handleFeaturesAlieses(taskParams)
    assert isinstance(taskParams['features'], list)

def checkBuildResults(testSuit, cmdLine, resultExists, withTests = False):

    def makeConfDict(conf, deep):
        result = AutoDict()
        _conf = AutoDict(vars(conf))
        for k in KNOWN_CONF_PARAM_NAMES:
            if deep:
                result[k] = deepcopy(_conf[k])
            else:
                result[k] = copy(_conf[k])
        return result

    _conf = makeConfDict(testSuit.projectConf, deep = True)

    # checks for target files
    processConfHandlerWithCLI(testSuit, cmdLine)
    buildtype = testSuit.confHandler.selectedBuildType
    isWindows = PLATFORM == 'windows'

    for taskName, taskParams in testSuit.confHandler.tasks.items():

        handleTaskFeatures(testSuit, taskParams)
        features = taskParams['features']

        if not withTests and 'test' in features:
            # ignore test tasks
            continue

        if not [ x for x in features if x in TASK_WAF_MAIN_FEATURES ]:
            # check only with features from TASK_WAF_MAIN_FEATURES
            continue

        fileNamePattern, isExe = getTargetPattern(testSuit, taskName, features)
        target = taskParams.get('target', taskName)
        targetpath = joinpath(testSuit.confPaths.buildout, buildtype,
                                fileNamePattern % target)

        assert os.path.isfile(targetpath) == resultExists
        if resultExists and isExe:
            assert os.access(targetpath, os.X_OK)

        isSharedLib = any([x.endswith('shlib') for x in features])
        if isSharedLib and isWindows:
            targetpath = joinpath(os.path.dirname(targetpath),
                                '%s.lib' % target)
            assert os.path.isfile(targetpath) == resultExists

    # check original buildconf was not changed
    assert _conf == makeConfDict(testSuit.projectConf, deep = False)

@pytest.mark.usefixtures("unsetEnviron")
class TestBase(object):

    def _runZm(self, cmdline):
        return runZm(self, utils.toList(cmdline) + ['-v'])

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
        checkBuildResults(self, cmdLine, False)
        assert os.path.isfile(self.confPaths.wafcachefile)
        assert os.path.isfile(self.confPaths.zmcmnconfset)

        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

    def testBuild(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

    def testBuildAndBuild(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

        # simple rebuild
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

    def testBuildAndClean(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

        # clean
        cmdLine = ['clean']
        assert self._runZm(cmdLine)[0] == 0
        assert os.path.isdir(self.confPaths.buildroot)
        assert os.path.isdir(self.confPaths.buildout)
        assert os.path.isfile(self.confPaths.wafcachefile)
        assert os.path.isfile(self.confPaths.zmcmnconfset)
        checkBuildResults(self, cmdLine, False)

    def testBuildAndDistclean(self, allprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

        # distclean
        assert os.path.isdir(self.confPaths.buildroot)
        cmdLine = ['distclean']
        assert self._runZm(cmdLine)[0] == 0
        assert not os.path.exists(self.confPaths.buildroot)

    @pytest.mark.skipif(PLATFORM == 'windows',
                        reason = 'I have no useful windows installation for tests')
    def testCustomToolchain(self, customtoolchains):

        cmdLine = ['build']
        returncode, stdout, stderr =  self._runZm(cmdLine)
        assert returncode == 0
        checkBuildResults(self, cmdLine, True)

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
            events = self._runAndGather(cmdLines[0], False)
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

        # clean
        cmdLine = ['clean']
        assert runZm(self, cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, False, True)
        assert os.path.isdir(self.confPaths.buildroot)
        assert os.path.isdir(self.confPaths.buildout)
        assert os.path.isfile(self.confPaths.wafcachefile)
        assert os.path.isfile(self.confPaths.zmcmnconfset)

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

        # clean
        cmdLine = ['clean']
        assert runZm(self, cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, False, True)
        assert os.path.isdir(self.confPaths.buildroot)
        assert os.path.isdir(self.confPaths.buildout)
        assert os.path.isfile(self.confPaths.wafcachefile)
        assert os.path.isfile(self.confPaths.zmcmnconfset)

    def testCmdTestRTAllVariants(self, projects):

        self._checkFeatureRTAllVariants([
            ['test', '--build-tests', 'no', '--run-tests', 'all'],
            ['test', '--build-tests', 'yes', '--run-tests', 'all'],
            ['test', '--build-tests', 'yes', '--run-tests', 'on-changes'],
        ])

class TestIndyCmd(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    def testZipAppCmd(self, tmpdir):
        cmdLine = ['zipapp']
        self.cwd = str(tmpdir.realpath())
        exitcode, stdout, stderr = runZm(self, cmdLine)
        assert exitcode == 0
        zipAppPath = joinpath(self.cwd, zipapp.ZIPAPP_NAME)
        assert os.path.isfile(zipAppPath)
        assert iszip(zipAppPath)

    def testVersionCmd(self, tmpdir):
        cmdLine = ['version']
        self.cwd = str(tmpdir.realpath())
        exitcode, stdout, stderr = runZm(self, cmdLine)
        assert exitcode == 0
        assert 'version' in stdout

    def testSysInfoCmd(self, tmpdir):
        cmdLine = ['sysinfo']
        self.cwd = str(tmpdir.realpath())
        exitcode, stdout, stderr = runZm(self, cmdLine)
        assert exitcode == 0
        assert 'information' in stdout

@pytest.mark.usefixtures("unsetEnviron")
class TestAutoconfig(object):

    cinfo = CompilersInfo

    @pytest.fixture(params = getZmExecutables())
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    @pytest.fixture(params = [joinpath('cpp', '02-simple')])
    def project(self, request, tmpdir):

        self.testdir = None

        def teardown():
            if request.node.rep_call.failed:
                printOutputs(self)
            elif self.testdir:
                zmdir = joinpath(self.testdir, 'zenmake')
                if os.path.isdir(zmdir):
                    shutil.rmtree(zmdir, ignore_errors = True)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

        self.testdir = os.path.abspath(joinpath(self.cwd, os.pardir))

    @pytest.fixture(params = cinfo.allFlagVars() + cinfo.allVarsToSetCompiler())
    def toolEnvVar(self, request):
        self.toolEnvVar = request.param

    def testEnvVars(self, allZmExe, project, toolEnvVar):

        # first run
        cmdLine = ['build']
        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0

        # then it should be checked

        # Such a way breaks building but here is testing of reacting, not building.
        os.environ[self.toolEnvVar] = cmn.randomstr()
        _, stdout, _ = runZm(self, cmdLine)
        assert "Setting top to" in stdout
        assert "Setting out to" in stdout

    def testConfChanged(self, allZmExe, project):

        # first run
        cmdLine = ['build']
        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0

        # then it should be checked

        buildConfFile = joinpath(self.cwd, 'buildconf.py')
        assert os.path.isfile(buildConfFile)

        with open(buildConfFile, 'r') as file:
            lines = file.readlines()
        lines.append("somevar = 'qq'\n")
        with open(buildConfFile, 'w') as file:
            file.writelines(lines)

        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0
        assert "Setting top to" in stdout
        assert "Setting out to" in stdout

        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0
        assert "Setting top to" not in stdout
        assert "Setting out to" not in stdout

    def testVerChanged(self, project):

        zmdir = joinpath(self.testdir, 'zenmake')
        shutil.copytree(cmn.ZENMAKE_DIR, zmdir)

        self.zmExe = [PYTHON_EXE, zmdir]

        # first run
        cmdLine = ['build']
        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0

        # then it should be checked
        parsed = version.parseVersion(version.current())
        gr = parsed.groups()
        changedVer = '.'.join(gr[:3]) + '-' + cmn.randomstr(10)

        filePath = joinpath(zmdir, version.VERSION_FILE_NAME)
        with io.open(filePath, 'wt') as file:
            file.write(pyutils.texttype(changedVer))

        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0
        assert "Setting top to" in stdout
        assert "Setting out to" in stdout

        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0
        assert "Setting top to" not in stdout
        assert "Setting out to" not in stdout

@pytest.mark.usefixtures("unsetEnviron")
class TestInstall(object):

    @pytest.fixture(params = getZmExecutables())
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    @pytest.fixture(params = FORINSTALL_PRJDIRS)
    def project(self, request, tmpdir):

        def teardown():
            if request.node.rep_call.failed:
                printOutputs(self)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def _checkInstallResults(self, cmdLine, check):

        env = ConfigSet()
        env.PREFIX = check.prefix
        env.BINDIR = check.bindir
        env.LIBDIR = check.libdir

        assert os.path.isdir(check.destdir)

        isWindows = PLATFORM == 'windows'

        targets = set()
        processConfHandlerWithCLI(self, cmdLine)
        for taskName, taskParams in self.confHandler.tasks.items():

            handleTaskFeatures(self, taskParams)
            features = taskParams['features']

            if 'test' in taskParams['features']:
                # ignore tests
                continue

            if not [ x for x in features if x in TASK_WAF_MAIN_FEATURES ]:
                # check only with features from TASK_WAF_MAIN_FEATURES
                continue

            isStLib = any([x.endswith('stlib') for x in features])
            if isStLib: # static libs aren't installed
                continue

            fileNamePattern, isExe = getTargetPattern(self, taskName, features)
            target = taskParams.get('target', taskName)
            targetpath = fileNamePattern % target

            if 'install-path' not in taskParams:
                targetpath = joinpath(check.bindir if isExe else check.libdir, targetpath)
            else:
                installPath = taskParams.get('install-path', '')
                if not installPath:
                    continue

                installPath = os.path.normpath(utils.substVars(installPath, env))
                targetpath = joinpath(installPath, targetpath)

            if check.destdir:
                targetpath = joinpath(check.destdir, os.path.splitdrive(targetpath)[1].lstrip(os.sep))
            assert os.path.isfile(targetpath)
            if isExe:
                assert os.access(targetpath, os.X_OK)

            targets.add(targetpath)

            isSharedLib = any([x.endswith('shlib') for x in features])
            if isSharedLib and isWindows:
                targetpath = joinpath(os.path.dirname(targetpath), '%s.lib' % target)
                assert os.path.isfile(targetpath)
                targets.add(targetpath)

        for root, dirs, files in os.walk(check.destdir):
            for name in files:
                path = joinpath(root, name)
                assert path in targets

    def testInstallUninstall(self, allZmExe, project, tmpdir):

        testdir = str(tmpdir.realpath())
        destdir = joinpath(testdir, 'inst')

        cmdLine = ['install', '--destdir', destdir]
        exitcode, _, _ = runZm(self, cmdLine)
        assert exitcode == 0

        check = AutoDict(
            destdir = destdir,
            prefix = cli.DEFAULT_PREFIX,
        )
        check.bindir = joinpath(check.prefix, 'bin')
        check.libdir = joinpath(check.prefix, 'lib%s' % utils.libDirPostfix())

        self._checkInstallResults(cmdLine, check)

        cmdLine[0] = 'uninstall'
        exitcode, _, _ = runZm(self, cmdLine)
        assert exitcode == 0
        assert not os.path.exists(destdir)

        # custom prefix
        prefix = '/usr/my'
        cmdLine = ['install', '--destdir', destdir, '--prefix', prefix]
        exitcode, _, _ = runZm(self, cmdLine)
        assert exitcode == 0

        check = AutoDict(
            destdir = destdir,
            prefix = prefix.replace('/', os.sep),
        )
        check.bindir = joinpath(check.prefix, 'bin')
        check.libdir = joinpath(check.prefix, 'lib%s' % utils.libDirPostfix())

        self._checkInstallResults(cmdLine, check)

        cmdLine[0] = 'uninstall'
        exitcode, _, _ = runZm(self, cmdLine)
        assert exitcode == 0
        assert not os.path.exists(destdir)

        # custom prefix, bindir, libdir
        prefix = '/usr/my'
        bindir = '/bb'
        libdir = '/ll'
        cmdLine = ['install', '--destdir', destdir, '--prefix', prefix]
        cmdLine.extend(['--bindir', bindir, '--libdir', libdir])
        exitcode, _, _ = runZm(self, cmdLine)
        assert exitcode == 0

        check = AutoDict(
            destdir = destdir,
            prefix = prefix.replace('/', os.sep),
            bindir = bindir.replace('/', os.sep),
            libdir = libdir.replace('/', os.sep),
        )

        self._checkInstallResults(cmdLine, check)

        cmdLine[0] = 'uninstall'
        exitcode, _, _ = runZm(self, cmdLine)
        assert exitcode == 0
        assert not os.path.exists(destdir)

@pytest.mark.usefixtures("unsetEnviron")
class TestBuildRoot(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = _zmExes[request.param]

    @pytest.fixture(params = [joinpath('c', '02-simple'), joinpath('cpp', '02-simple')])
    def project(self, request, tmpdir):

        def teardown():
            if request.node.rep_call.failed:
                printOutputs(self)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def testInCLI(self, project):

        cmdLine = ['build', '-o', '_bld']
        assert runZm(self, cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)
        assert self.confPaths.buildroot == joinpath(self.confPaths.buildconfdir, '_bld')

    def testInEnv(self, project, monkeypatch):

        monkeypatch.setenv('BUILDROOT', '_bld_')
        env = { 'BUILDROOT' : '_bld_' }
        cmdLine = ['build']
        assert runZm(self, cmdLine, env)[0] == 0
        checkBuildResults(self, cmdLine, True)
        assert self.confPaths.buildroot == joinpath(self.confPaths.buildconfdir, '_bld_')
