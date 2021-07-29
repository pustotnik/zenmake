# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = unused-argument, no-member, attribute-defined-outside-init
# pylint: disable = too-many-lines, too-many-branches, too-many-statements

"""
 Copyright (c) 2019-2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import re

import pytest
from zm import utils
from zm.constants import PLATFORM
from zm.constants import BUILDCONF_FILENAMES

import tests.common as cmn
from tests.func_utils import *

CUSTOM_TOOLCHAIN_PRJDIR = joinpath('cpp', '05-custom-toolchain')

BY_REGEXPS = tuple('byregexps') # for ability to have non string dict key
RE_ALL_D     = '^d/'
RE_ALL_LUA   = '^lua/'
RE_ALL_FC    = '^fortran/'
RE_ALL_DBUS  = '^dbus/'
RE_ALL_GTK3  = '^gtk3/'
RE_ALL_SDL2  = '^sdl2/'
RE_EXT_DEPS  = '^external-deps/'

TEST_CONDITIONS = {
    CUSTOM_TOOLCHAIN_PRJDIR: dict( os = ['linux', 'darwin'], ),
    joinpath('asm', '01-simple-gas') : dict( os = ['linux']),
    joinpath('asm', '02-simple-nasm') :
        #dict( os = ['linux'], py = ['3.5', '3.6', '3.7', '3.8', '3.9', '3.10']),
        dict( os = ['linux']),
    joinpath('c', '06-strip-release') : dict( os = ['linux']),
    BY_REGEXPS: [
        dict(regexp = RE_ALL_D, condition = dict( os = ['linux', 'darwin'], )),
        dict(regexp = RE_ALL_LUA, condition = dict( os = ['linux'], )),
        dict(regexp = RE_ALL_FC, condition = dict( os = ['linux'], )),
        dict(regexp = RE_ALL_DBUS, condition = dict( os = ['linux'], )),
        dict(regexp = RE_ALL_GTK3, condition = dict( os = ['linux'], )),
        dict(regexp = RE_ALL_SDL2, condition = dict( os = ['linux'], )),
        dict(regexp = RE_EXT_DEPS + '1-makefile',
            condition = dict( os = ['linux', 'darwin'], )),
    ],
}

def collectAllProjectDirs():
    for path in TEST_CONDITIONS:
        if path == BY_REGEXPS:
            continue
        path = joinpath(cmn.TEST_PROJECTS_DIR, path)
        assert isdir(path)

    result = []
    dirWithConf = None
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):

        if not any(x in BUILDCONF_FILENAMES for x in filenames):
            continue

        if not dirWithConf:
            dirWithConf = dirpath
        elif dirpath.startswith(dirWithConf):
            #collect only top-level configs
            continue
        else:
            dirWithConf = dirpath

        if os.path.isfile(os.path.join(dirpath, '.dontbuild')):
            # ignore this dir
            continue

        prjdir = os.path.relpath(dirpath, cmn.TEST_PROJECTS_DIR)
        condition = TEST_CONDITIONS.get(prjdir, None)
        if not condition:
            for line in TEST_CONDITIONS[BY_REGEXPS]:
                if re.search(line['regexp'], prjdir.replace('\\', '/'), re.U):
                    condition = line['condition']
                    break
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

ALL_PROJECTS = collectAllProjectDirs()

def filterBaseProjectDirs():
    basePrjTypes = ('c', 'cpp', 'mixed', 'external-deps', 'fortran')
    result = []
    for path in ALL_PROJECTS:
        for ptype in basePrjTypes:
            if path.startswith(ptype + os.path.sep):
                result.append(path)
    return result

BASE_PROJECTS = filterBaseProjectDirs()

@pytest.mark.usefixtures("unsetEnviron")
class TestBase(object):

    def _runZm(self, cmdline):
        return runZm(self, utils.toList(cmdline) + ['-v'])

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = ALL_PROJECTS)
    def allprojects(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    @pytest.fixture(params = BASE_PROJECTS)
    def baseprojects(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

    @pytest.fixture(params = [CUSTOM_TOOLCHAIN_PRJDIR])
    def customtoolchains(self, request, tmpdir):
        setupTest(self, request, tmpdir)

    def testConfigureAndBuild(self, allprojects):

        cmdLine = ['configure']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, False)
        assert isfile(self.confPaths.wafcachefile)
        assert isfile(self.confPaths.zmmetafile)

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

    def testBuildAndClean(self, baseprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

        # clean
        cmdLine = ['clean']
        assert self._runZm(cmdLine)[0] == 0
        assert isdir(self.confPaths.buildroot)
        assert isdir(self.confPaths.buildout)
        assert isfile(self.confPaths.wafcachefile)
        assert isfile(self.confPaths.zmmetafile)
        checkBuildResults(self, cmdLine, False)

    def testBuildAndCleanAll(self, baseprojects):

        # simple build
        cmdLine = ['build']
        assert self._runZm(cmdLine)[0] == 0
        checkBuildResults(self, cmdLine, True)

        # cleanall
        assert isdir(self.confPaths.buildroot)
        cmdLine = ['cleanall']
        assert self._runZm(cmdLine)[0] == 0
        assert not os.path.exists(self.confPaths.buildroot)

    @pytest.mark.skipif(PLATFORM == 'windows',
                        reason = 'No useful windows installation for tests')
    def testCustomToolchain(self, customtoolchains):

        cmdLine = ['build']
        returncode, stdout, _ =  self._runZm(cmdLine)
        assert returncode == 0
        checkBuildResults(self, cmdLine, True)

        tasks = getBuildTasks(self.confManager)
        for taskParams in tasks.values():
            toolchain = taskParams.get('toolchain', [])
            assert toolchain
            if not toolchain[0].startswith('custom-'):
                continue
            emukind = toolchain[0][7:]
            assert emukind
            checkmsg = '%s wrapper for custom toolchain test' % emukind
            assert checkmsg in stdout
