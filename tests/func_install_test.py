# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = unused-argument, no-member, attribute-defined-outside-init
# pylint: disable = too-many-lines, too-many-branches, too-many-statements

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

import pytest
from zm import cli, utils
from zm.pyutils import viewitems
from zm.autodict import AutoDict
from zm.constants import PLATFORM
from zm.features import TASK_TARGET_FEATURES

from tests.func_utils import *

FORINSTALL_PRJDIRS = [
    joinpath('cpp', '09-complex-unittest'),
    joinpath('subdirs', '2-complex'),
]

@pytest.mark.usefixtures("unsetEnviron")
class TestInstall(object):

    @pytest.fixture(params = getZmExecutables())
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = FORINSTALL_PRJDIRS)
    def project(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def _checkInstallResults(self, cmdLine, check):

        env = ConfigSet()
        env.PREFIX = check.prefix
        env.BINDIR = check.bindir
        env.LIBDIR = check.libdir

        assert isdir(check.destdir)

        isWindows = PLATFORM == 'windows'

        targets = set()
        processConfManagerWithCLI(self, cmdLine)
        tasks = getBuildTasks(self.confManager)
        for taskName, taskParams in viewitems(tasks):

            handleTaskFeatures(self, taskParams)
            features = taskParams['features']

            if 'test' in taskParams['features']:
                # ignore tests
                continue

            if not [ x for x in features if x in TASK_TARGET_FEATURES ]:
                # check only with features from TASK_TARGET_FEATURES
                continue

            taskEnv = getTaskEnv(self, taskName)
            fpattern, targetKind = getTargetPattern(taskEnv, features)

            if targetKind == 'stlib':
                # static libs aren't installed
                continue

            isExe = targetKind == 'exe'
            target = taskParams.get('target', taskName)

            if 'install-path' not in taskParams:
                targetdir = check.bindir if isExe else check.libdir
            else:
                installPath = taskParams.get('install-path', '')
                if not installPath:
                    continue

                env = env.derive()
                env.update(taskParams.get('substvars', {}))
                installPath = os.path.normpath(utils.substVars(installPath, env))
                targetdir = installPath

            if check.destdir:
                targetdir = joinpath(check.destdir,
                                      os.path.splitdrive(targetdir)[1].lstrip(os.sep))

            targetpath = joinpath(targetdir, fpattern % target)
            targets.add(targetpath)

            if targetKind == 'exe':
                assert os.access(targetpath, os.X_OK)

            if targetKind == 'shlib':
                verNum = taskParams.get('ver-num', None)
                if verNum:
                    nums = verNum.split('.')
                    if targetpath.endswith('.dylib'):
                        fname = fpattern % (target + '.' + nums[0])
                        targets.add(joinpath(targetdir, fname))
                        fname = fpattern % (target + '.' + verNum)
                        targets.add(joinpath(targetdir, fname))
                    else:
                        targets.add(targetpath + '.' + nums[0])
                        targets.add(targetpath + '.' + verNum)

                    if taskEnv.DEST_BINFMT == 'pe':
                        fname = fpattern % (target + '-' + nums[0])
                        targets.add(joinpath(targetdir, fname))

                if isWindows:
                    targetpath = joinpath(targetdir, '%s.lib' % target)
                    assert isfile(targetpath)
                    targets.add(targetpath)

        for root, _, files in os.walk(check.destdir):
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
