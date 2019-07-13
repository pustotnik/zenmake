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
import unittest
import tests.common as cmn
import zm.utils
import zm.buildconfutil

joinpath = os.path.join

PLATFORM = zm.utils.platform()
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PROJECTS_DIR = joinpath(cmn.sharedtmpdir, 'projects')
ZM_BIN = os.path.normpath(joinpath(TESTS_DIR, os.path.pardir, "zenmake"))

class _BaseProjectBuild(object):

    def _runZm(self, cmdline):
        timeout = 60 * 5
        proc = subprocess.Popen(cmdline, stdout = subprocess.PIPE,
                            stderr = subprocess.STDOUT, cwd = self.cwd,
                            env = os.environ.copy(), universal_newlines = True)
        if zm.utils.PY3:
            stdout, stderr = proc.communicate(timeout = timeout)
        else:
            stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            print('\n' + stdout)
        return proc.returncode

    def _cleanDirs(self):
        for path in (self.buildconf.buildroot, self.buildconf.buildsymlink):
            if not path:
                continue
            path = zm.utils.unfoldPath(self.cwd, path)
            if os.path.isdir(path) and os.path.exists(path):
                shutil.rmtree(path, ignore_errors = True)
            elif os.path.islink(path) and os.path.lexists(path):
                os.remove(path)
            elif os.path.exists(path) and os.path.isfile(path):
                os.remove(path)

    def setUp(self):
        self.longMessage = True
        sys.path.insert(0, self.cwd)
        self.buildconf = zm.buildconfutil.loadConf()
        self._cleanDirs()

    def tearDown(self):
        self._cleanDirs()
        sys.path.remove(self.cwd)

    def testJustBuild(self):
        pythonbin = sys.executable
        if not pythonbin:
            pythonbin = 'python'
        cmdLine = [pythonbin, ZM_BIN, 'build']
        self.assertEqual(self._runZm(cmdLine), 0)

def collectProjectDirs():
    result = []
    for dirpath, _, filenames in os.walk(TEST_PROJECTS_DIR):
        if 'buildconf.py' in filenames:
            result.append(os.path.relpath(dirpath, TEST_PROJECTS_DIR))
    result.sort()
    return result

# Copy projects into tmp dir
shutil.copytree(joinpath(TESTS_DIR, 'projects'), TEST_PROJECTS_DIR)

# Declare test cases for each project dynamically
allprojects = collectProjectDirs()
for cwd in allprojects:
    suffix = ''
    for p in cwd.split(os.path.sep):
        suffix += p.capitalize() + '_'
    if suffix[-1] == '_':
        suffix = suffix[0:-1]
    suffix = suffix.replace('-', '_').replace(' ', '_')
    clsname = 'BuildProject_' + suffix
    base = (_BaseProjectBuild, unittest.TestCase)
    attrs = dict(cwd = joinpath(TEST_PROJECTS_DIR, cwd))
    globals()[clsname] = type(clsname, base, attrs)