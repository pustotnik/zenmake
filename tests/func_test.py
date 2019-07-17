# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import subprocess
import shutil
import pytest
from waflib import Build
from waflib.ConfigSet import ConfigSet
import tests.common as cmn
from zm import utils, buildconfutil, assist, cli
import starter

joinpath = os.path.join

PLATFORM = utils.platform()
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
ZM_BIN = os.path.normpath(joinpath(TESTS_DIR, os.path.pardir, "zenmake"))

# Copy projects into tmp dir
shutil.copytree(joinpath(TESTS_DIR, 'projects'), cmn.TEST_PROJECTS_DIR)

def collectProjectDirs():
    result = []
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.py' in filenames:
            result.append(os.path.relpath(dirpath, cmn.TEST_PROJECTS_DIR))
    result.sort()
    return result

class TestProject(object):

    def _runZm(self, cmdline):
        timeout = 60 * 5
        proc = subprocess.Popen(cmdline, stdout = subprocess.PIPE,
                            stderr = subprocess.STDOUT, cwd = self.cwd,
                            env = os.environ.copy(), universal_newlines = True)
        if utils.PY3:
            stdout, stderr = proc.communicate(timeout = timeout)
        else:
            stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            print('\n' + stdout)
        return proc.returncode

    @pytest.fixture(params = collectProjectDirs(), autouse = True)
    def setup(self, request):
        def teardown():
            pass

        request.addfinalizer(teardown)

        self.cwd = joinpath(cmn.TEST_PROJECTS_DIR, request.param)

    def testBuild(self, unsetEnviron):
        pythonbin = sys.executable
        if not pythonbin:
            pythonbin = 'python'
        cmdLine = [pythonbin, ZM_BIN, 'build', '-v']
        assert 0 == self._runZm(cmdLine)

        # checks for target files
        projectConf = buildconfutil.loadConf('buildconf',
                                            self.cwd, withImport = False)

        confHandler = assist.BuildConfHandler(projectConf)
        cmd, _ = starter.handleCLI(confHandler, cmdLine[1:], True)
        confHandler.handleCmdLineArgs(cmd)
        confPaths = confHandler.confPaths
        buildtype = confHandler.selectedBuildType

        for taskName, taskParams in confHandler.tasks.items():
            taskVariant = assist.getTaskVariantName(buildtype, taskName)
            cacheConfFile = assist.makeCacheConfFileName(confPaths.zmcachedir, taskVariant)
            env = ConfigSet(cacheConfFile)
            target = taskParams.get('target', taskName)
            fileNamePattern = '%s'
            features = taskParams.get('features', '').split()
            for feature in features:
                # find pattern via brute force :)
                key = feature + '_PATTERN'
                if key not in env:
                    continue
                fileNamePattern = env[key]

            targetpath = joinpath(confPaths.buildout, buildtype, fileNamePattern % target)
            assert os.path.exists(targetpath)
            assert os.path.isfile(targetpath)