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
from zm import pyutils, assist, cli, utils
from zm.buildconf import loader as bconfloader
from zm.buildconf.handler import BuildConfHandler
from zm.constants import ZENMAKE_COMMON_FILENAME, PLATFORM
import starter

joinpath = os.path.join

ZM_BIN = os.path.normpath(joinpath(cmn.TESTS_DIR, os.path.pardir, "zenmake"))
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

def runZm(cwd, cmdline, env = None, printStdOutOnFailed = True):

    cmdLine = [PYTHON_EXE, ZM_BIN] + utils.toList(cmdline)

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
    if proc.returncode != 0 and printStdOutOnFailed:
        print('\n' + stdout)
    return proc.returncode, stdout, stderr

def setupTest(self, request, tmpdir):

    testName = request.node.originalname
    if not testName:
        testName = request.node.name

    #projectDirName = request.param
    projectDirName = 'prj'

    tmpdirForTests = cmn.SHARED_TMP_DIR
    #tmptestDir = joinpath(tmpdirForTests, testName, projectDirName)
    tmptestDir = joinpath(tmpdirForTests, projectDirName)
    shutil.rmtree(tmptestDir, ignore_errors = True)
    #tmptestDir = joinpath(str(tmpdir.realpath()), projectDirName)

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
class TestProject(object):

    def _runZm(self, cmdline):
        return runZm(self.cwd, utils.toList(cmdline) + ['-v'])

    def _checkBuildResults(self, cmdLine, resultExists):
        # checks for target files
        cmdLine = list(cmdLine)
        cmdLine.insert(0, ZM_BIN)
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


    @pytest.fixture(params = collectProjectDirs())
    def allprojects(self, request, tmpdir):

        def teardown():
            pass

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

        cmd, _ = starter.handleCLI(self.confHandler, [ZM_BIN] + cmdLine, True)
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
                output = cmdOutput
            )
            cmdEvents = []
            cmdOutput = []
            cmdIndexes = defaultdict(dict)
            continue

        m = re.match(r"^\s*\[\s*\d+/\d+\]\s+Linking\s+.+\%s(lib)?(\w+)" % sep, line)
        if m:
            task = m.group(2)
            cmdEvents.append(['linking', task])
            cmdIndexes['linking'][task] = len(cmdEvents) - 1
            continue

        m = re.match(r"^\s*\[\s*\d+/\d+\]\s+Running\s+command\s+.*?\'([\w\s.\-]+)\'$", line)
        if m:
            task = m.group(1)
            cmdEvents.append(['running', task])
            cmdIndexes['running'][task] = len(cmdEvents) - 1
            continue


        terminators = (r"^\s*\[\s*\d+/\d+\]\s+.+", r"^Waf:\s+")
        if any([ bool(re.match(expr, line)) for expr in terminators ]):
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

    @pytest.fixture(params = [COMPLEX_UNITTEST_PRJDIR])
    def projects(self, request, tmpdir):
        setupTest(self, request, tmpdir)

    def testBasis(self, projects):

        cmdLine = ['build']
        returncode, stdout, stderr = runZm(self.cwd, cmdLine)
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
        returncode, _, _ = runZm(self.cwd, cmdLine, env,
                                 printStdOutOnFailed = False)
        assert returncode != 0

@pytest.mark.usefixtures("unsetEnviron")
class TestFeatureTest(object):
    pass