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

import os

import pytest
from zm.utils import substBuiltInVars
from zm import installdirvars
from zm.autodict import AutoDict
from zm.constants import PLATFORM, DEFAULT_BUILDWORKNAME
from zm.features import TASK_TARGET_FEATURES

from tests.func_utils import *

FORINSTALL_PRJDIRS = [
    joinpath('cpp', '09-complex-unittest'),
    joinpath('subdirs', '2-complex'),
]

def getInstallFixtureParams():

    fixtures = []
    dvarsCfgMap = installdirvars.CONFIG_MAP
    defaultVars = {
        name:dvarsCfgMap[name].default
        for name in ('prefix', 'bindir', 'libdir')
    }

    #### 1
    params = AutoDict(**defaultVars)
    params.installArgs = []

    fixtures.append(AutoDict(id = len(fixtures) + 1, **params))

    #### 2
    params = AutoDict(
        prefix = '/usr/my',
        bindir = defaultVars['bindir'],
        libdir = defaultVars['libdir']
    )
    params.installArgs = ['--prefix', params.prefix]

    fixtures.append(AutoDict(id = len(fixtures) + 1, **params))

    #### 3
    params = AutoDict(
        prefix = '/usr/my',
        bindir = '/bb',
        libdir = '/ll',
    )

    params.installArgs = [
        '--prefix', params.prefix,
        '--bindir', params.bindir,
        '--libdir', params.libdir
    ]

    fixtures.append(AutoDict(id = len(fixtures) + 1, **params))

    #### 4
    params = AutoDict(
        prefix = '/usr/my',
        bindir = 'bb-aa',
        libdir = 'll_dd',
    )

    params.installArgs = [
        '--prefix', params.prefix,
        '--bindir', params.bindir,
        '--libdir', params.libdir
    ]

    fixtures.append(AutoDict(id = len(fixtures) + 1, **params))

    #### 5
    params = AutoDict(
        prefix = 'usr2/my',
        bindir = defaultVars['bindir'],
        libdir = 'mylib',
    )

    params.installArgs = [
        '--prefix', params.prefix,
        '--libdir', params.libdir
    ]

    fixtures.append(AutoDict(id = len(fixtures) + 1, **params))

    ### store ids
    for item in fixtures:
        item['id'] = str(item['id'])

    pairs = []
    for i, _ in enumerate(fixtures):
        cur = fixtures[i]
        nex = fixtures[i+1] if i+1 < len(fixtures) else fixtures[0]
        pairs.append([cur, nex])

    return pairs

INSTALL_FIXTURE_PARAMS = getInstallFixtureParams()

def checkBuildWorkDir(testSuit):
    """
    Check that the @bld directory exists and isn't empty
    """

    buildtypedir = testSuit.confManager.root.selectedBuildTypeDir
    buildworkdir = joinpath(buildtypedir, DEFAULT_BUILDWORKNAME)

    assert os.path.isdir(buildworkdir)
    assert len(os.listdir(buildworkdir)) > 0

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

        check = check.copy()
        assert isdir(check.destdir)

        isWindows = PLATFORM == 'windows'

        targets = set()
        processConfManagerWithCLI(self, cmdLine)

        checkBuildWorkDir(self)

        svars = self.confManager.root.builtInVars
        for name in ('prefix', 'bindir', 'libdir'):
            check[name] = substBuiltInVars(check[name], svars)
            if not os.path.isabs(check[name]):
                check[name] = '/' + check[name]
            check[name] = check[name].replace('/', os.sep)

        tasks = getBuildTasks(self.confManager)
        for taskName, taskParams in tasks.items():

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

                installPath = os.path.normpath(utils.substBuiltInVars(installPath, svars))
                targetdir = installPath

            if not os.path.isabs(targetdir):
                targetdir = joinpath(check.prefix, targetdir)

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

    @pytest.fixture(params = INSTALL_FIXTURE_PARAMS, ids = lambda x: x[0]['id'])
    def installFixtures(self, request, tmpdir):

        testdir = str(tmpdir.realpath())
        fixturesList = request.param.copy()
        for fixtures in fixturesList:
            fixtures['destdir'] = joinpath(testdir, 'inst')

        return fixturesList

    def test(self, allZmExe, project, installFixtures):

        for fixtures in installFixtures:
            destdir = fixtures.destdir

            cmdLine = ['install', '--destdir', destdir]
            cmdLine.extend(fixtures.installArgs)
            exitcode, _, _ = runZm(self, cmdLine)
            assert exitcode == 0

            self._checkInstallResults(cmdLine, fixtures)

            cmdLine[0] = 'uninstall'
            exitcode, _, _ = runZm(self, cmdLine)
            assert exitcode == 0
            assert not os.path.exists(destdir)

#############################################################################
#############################################################################

FORINSTALLFILES_PRJDIRS = [
    joinpath('mixed', '01-cshlib-cxxprogram'),
]

@pytest.mark.usefixtures("unsetEnviron")
class TestInstallFiles(object):

    @pytest.fixture(params = getZmExecutables())
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = FORINSTALLFILES_PRJDIRS)
    def project(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    def _prepareFixtures(self, fixtures, testdir):

        fixtures['destdir'] = joinpath(testdir, 'inst')

        if self.testDirPath == FORINSTALLFILES_PRJDIRS[0]:

            dirprfx = '$(appdatadir)/scripts'

            files = [
                { 'path' : dirprfx + '/my-script.py', 'chmod' : 0o755, },
                { 'path' : dirprfx + '/test.py', 'chmod' : 0o755, },
                { 'path' : dirprfx + '/asd/test2.py', 'chmod' : 0o755, },
                #{ 'path' : dirprfx + '/my-script.link.py', 'chmod' : 0o755, },
                { 'path' : dirprfx + '2/my-script.py', 'chmod' : 0o755, },
                { 'path' : dirprfx + '2/test.py', 'chmod' : 0o755, },
                { 'path' : dirprfx + '3/my-script.py', 'chmod' : 0o644, },
                { 'path' : dirprfx + '3/test.py', 'chmod' : 0o644, },
                { 'path' : dirprfx + '3/test2.py', 'chmod' : 0o644, },
                { 'path' : dirprfx + '/mtest.py', 'chmod' : 0o750 },
            ]

            if PLATFORM == 'linux':
                files.extend([
                    { 'path' : dirprfx + '/mtest-link.py', 'linkto' : dirprfx + '/mtest.py' },
                ])

            if PLATFORM != 'windows':
                files.extend([
                    { 'path' : dirprfx + '/my-script.link.py', 'chmod' : 0o755, },
                ])
                files.extend([
                    { 'path' : dirprfx + '2/my-script.link.py', 'linkto' : './my-script.py' },
                ])
        else:
            # unknown project, forgot to add ?
            assert False

        for item in files:
            item['path'] = item['path'].replace('/', os.sep)

        fixtures['files'] = files

        return fixtures

    @pytest.fixture(params = INSTALL_FIXTURE_PARAMS, ids = lambda x: x[0]['id'])
    def installFixtures(self, request, tmpdir):

        testdir = str(tmpdir.realpath())
        fixturesList = request.param
        fixturesList = [self._prepareFixtures(x.copy(), testdir) for x in fixturesList]

        return fixturesList

    def test(self, allZmExe, project, installFixtures):

        def handlePath(path, svars):
            return substBuiltInVars(path, svars).replace('/', os.sep)

        for fixtures in installFixtures:

            fixtures = fixtures.copy()
            destdir = fixtures.destdir

            cmdLine = ['install', '--destdir', destdir]
            cmdLine.extend(fixtures.installArgs)
            exitcode, _, _ = runZm(self, cmdLine)
            assert exitcode == 0

            processConfManagerWithCLI(self, cmdLine)
            checkBuildWorkDir(self)

            svars = self.confManager.root.builtInVars

            for item in fixtures['files']:
                filepath = handlePath(item['path'], svars)
                if os.path.isabs(filepath):
                    # path must be relative because of os.path.join
                    filepath = os.path.splitdrive(filepath)[1].lstrip(os.sep)
                filepath = joinpath(destdir, filepath)

                if 'linkto' in item:
                    linkto = handlePath(item['linkto'], svars)
                    assert islink(filepath)
                    assert linkto == os.readlink(filepath)
                else:
                    assert isfile(filepath)
                    if PLATFORM != 'windows':
                        chmodExpected = oct(item.get('chmod', 0o644))[-3:]
                        chmodReal = oct(os.stat(filepath).st_mode)[-3:]
                        assert chmodReal == chmodExpected

            cmdLine[0] = 'uninstall'
            exitcode, _, _ = runZm(self, cmdLine)
            assert exitcode == 0
            assert not os.path.exists(destdir)
