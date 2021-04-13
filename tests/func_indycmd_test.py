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

from zipfile import is_zipfile as iszip

import pytest
from zm import zipapp

from tests.func_utils import *

class TestIndyCmd(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)

    def testZipAppCmd(self, tmpdir):
        cmdLine = ['zipapp']
        self.cwd = str(tmpdir.realpath())
        exitcode = runZm(self, cmdLine)[0]
        assert exitcode == 0
        zipAppPath = joinpath(self.cwd, zipapp.ZIPAPP_NAME)
        assert isfile(zipAppPath)
        assert iszip(zipAppPath)

    def testVersionCmd(self, tmpdir):
        cmdLine = ['version']
        self.cwd = str(tmpdir.realpath())
        exitcode, stdout, _ = runZm(self, cmdLine)
        assert exitcode == 0
        assert 'version' in stdout

    def testSysInfoCmd(self, tmpdir):
        cmdLine = ['sysinfo']
        self.cwd = str(tmpdir.realpath())
        exitcode, stdout, _ = runZm(self, cmdLine)
        assert exitcode == 0
        assert 'information' in stdout
