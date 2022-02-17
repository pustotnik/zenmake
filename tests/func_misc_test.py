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
import fnmatch
from distutils.spawn import find_executable

import pytest

from zm import utils
from zm.features import ToolchainVars
from zm.testing import loadFromJson
from tests.func_utils import *

@pytest.mark.usefixtures("unsetEnviron")
class TestParams(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = [joinpath('c', '02-simple'), joinpath('cpp', '04-complex')])
    def project(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        setupTest(self, request, tmpdir)

        return request.param

    def testBuildRootInCLI(self, project):

        env = { 'ZENMAKE_TESTING_MODE' : '1' }
        cmdLine = ['build', '-o', '_bld']
        assert runZm(self, cmdLine, env)[0] == 0
        checkBuildResults(self, cmdLine, resultExists = True, fakeBuild = True)
        assert self.confPaths.buildroot == joinpath(self.confPaths.buildconfdir, '_bld')

    def testBuildRootInEnv(self, project, monkeypatch):

        monkeypatch.setenv('BUILDROOT', '_bld_') # for checkBuildResults

        env = { 'BUILDROOT' : '_bld_', 'ZENMAKE_TESTING_MODE' : '1' }
        cmdLine = ['build']
        assert runZm(self, cmdLine, env)[0] == 0
        checkBuildResults(self, cmdLine, resultExists = True, fakeBuild = True)
        assert self.confPaths.buildroot == joinpath(self.confPaths.buildconfdir, '_bld_')

    @pytest.mark.skipif(PLATFORM != 'linux',
                        reason = "It's enough to test on linux only")
    def testToolchainVars(self, project):

        projectLang = os.path.split(project)[-2].replace('p', 'x')
        fixture = {
            'c' : {
                'gcc': {
                    'sysenvval' : 'gcc',
                    'compflags' : '',
                    'linkflags' : '',
                    'ldflags'   : '-Wl,-rpath,.',
                },
                'clang': {
                    'sysenvval' : 'clang',
                    'compflags' : '-O1 -g',
                    'linkflags' : '-Wl,-rpath,. ',
                    'ldflags'   : '',
                },
                'clang-path': {
                    'sysenvval' : find_executable('clang'),
                    'compflags' : '-O1 -g',
                    'linkflags' : '-Wl,-rpath,. ',
                    'ldflags'   : '',
                },
            },
            'cxx': {
                'g++': {
                    'sysenvval' : 'g++',
                    'compflags' : '-O2 -Wall',
                    'linkflags' : '-Wl,-rpath,. -Wl,--as-needed',
                    'ldflags'   : '-fsanitize=address',
                },
                'clang++': {
                    'sysenvval' : 'clang++',
                    'compflags' : '-O3 -Wall -Wextra',
                    'linkflags' : '-Wl,--as-needed -fsanitize=address',
                    'ldflags'   : '-Wl,-rpath,.',
                },
            },
        }

        def formExpectedFlags(flags):
            flags = utils.uniqueListWithOrder(reversed(flags))
            flags.reverse()
            return flags

        env = { 'ZENMAKE_TESTING_MODE' : '1' }
        cmdLine = ['build']
        sysEnvToolVar = ToolchainVars.sysVarToSetToolchain(projectLang)
        cfgEnvToolVar = ToolchainVars.cfgVarToSetToolchain(projectLang)
        compFlagsName = projectLang.upper() + 'FLAGS'

        # invalid name
        toolchain = 'invalid'
        env[sysEnvToolVar] = toolchain
        assert runZm(self, cmdLine, env)[0] != 0

        prjfixture = fixture[projectLang]

        for toolchain, info in prjfixture.items():

            env[sysEnvToolVar] = info['sysenvval']
            env[compFlagsName] = info['compflags']
            env['LINKFLAGS'] = info['linkflags']
            env['LDFLAGS'] = info['ldflags']

            assert runZm(self, ['distclean'])[0] == 0
            assert runZm(self, cmdLine, env)[0] == 0

            targets = obtainBuildTargets(self, cmdLine)
            checkBuildTargets(targets, resultExists = True, fakeBuild = True)

            confManager = processConfManagerWithCLI(self, cmdLine)
            buildout = confManager.root.confPaths.buildout

            paths = []
            patterns = '.* c4che config.log'.split()
            for root, dirs, files in os.walk(buildout):
                ignore = set()
                for pattern in patterns:
                    for name in fnmatch.filter(dirs, pattern):
                        dirs.remove(name) # don't visit sub directories
                    for name in fnmatch.filter(files, pattern):
                        ignore.add(name)

                paths += [os.path.join(root, x) for x in files if x not in ignore]

            for path in paths:
                with open(path, 'r') as f:
                    data = loadFromJson(f.read())
                zmTaskName = data['tgen-name']
                usedEnv = data['env']
                zmtasks = data['zmtasks']
                taskParams = zmtasks[zmTaskName]
                features = taskParams['features']
                targetKind = getTargetPattern(usedEnv, features)[1]

                # check toolchain
                assert usedEnv[cfgEnvToolVar] == [find_executable(info['sysenvval'])]

                isLink = data['is-link']
                if not isLink:
                    # check CFLAGS/CXXFLAGS
                    sysEnvFlags = env[compFlagsName].split()
                    bconfFlags = utils.toList(taskParams.get(compFlagsName.lower(), []))
                    expectedFlags = formExpectedFlags(bconfFlags + sysEnvFlags)
                    if targetKind == 'shlib':
                        # Waf adds this flag itself
                        expectedFlags = ['-fPIC'] + expectedFlags
                    assert usedEnv.get(compFlagsName, []) == expectedFlags
                else:
                    # check LINKFLAGS/LDFLAGS
                    for flagsName in ('linkflags', 'ldflags'):
                        sysEnvFlags = env[flagsName.upper()].split()
                        bconfFlags = utils.toList(taskParams.get(flagsName, []))
                        expectedFlags = formExpectedFlags(bconfFlags + sysEnvFlags)
                        if targetKind == 'shlib' and flagsName == 'linkflags':
                            # Waf adds this flag itself
                            expectedFlags = ['-shared'] + expectedFlags

                        assert usedEnv.get(flagsName.upper(), []) == expectedFlags
