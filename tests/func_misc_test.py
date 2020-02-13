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

import pytest

from tests.func_test_tools import *

@pytest.mark.usefixtures("unsetEnviron")
class TestBuildRoot(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture(params = [joinpath('c', '02-simple'), joinpath('cpp', '02-simple')])
    def project(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

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
