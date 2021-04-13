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

from zm.constants import PLATFORM
from tests.func_utils import *

TOOLCHAN_TO_ENVVAR = dict(
    dmd  = 'DC',
    ldc2 = 'DC',
    gdc  = 'DC',
)

PARAMS_CONFIG = {
    # D
    ('dmd', joinpath('d', '02-withlibs')) :
        dict( default = ('linux', 'darwin'), ci = ('darwin'), ),
    ('ldc2', joinpath('d', '02-withlibs')) :
        dict( default = ('linux', 'darwin'), ci = ('linux', 'darwin'), ),
    ('gdc', joinpath('d', '02-withlibs')) :
        dict( default = ('linux', ), ci = ('linux'), ),
}

def _gatherDistInfo():
    import csv

    result = {}

    with open("/etc/os-release") as f:
        reader = csv.reader(f, delimiter="=")
        for row in reader:
            if row:
                result[row[0]] = row[1]

    return result

def _generateParams():

    params = []

    isCI = os.environ.get('CI', None) == 'true'
    isTravisCI = isCI and os.environ.get('TRAVIS', None) == 'true'
    #isGitHubCI = isCI and os.environ.get('GITHUB_ACTIONS', None) == 'true'

    disableGDC = False

    # Due to bug with packages ldc + gdc:
    # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=827211
    if PLATFORM == 'linux':
        if isTravisCI:
            disableGDC = os.environ.get('TRAVIS_DIST', '') == 'xenial'
        else:
            info = _gatherDistInfo()
            nameId = info.get('ID')
            if nameId in ('debian', 'ubuntu'):
                codeName = info.get('VERSION_CODENAME')
                # do we need the debian codename ?
                disableGDC = codeName in ('xenial', )

    for item, condition in PARAMS_CONFIG.items():
        condition = condition['ci'] if isCI else condition['default']
        if PLATFORM in condition:
            if item[0] == 'gdc' and disableGDC:
                continue
            params.append(item)

    return params

@pytest.mark.usefixtures("unsetEnviron")
class TestToolchain(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)

    @pytest.mark.parametrize("toolchain, project", _generateParams())
    def testBuild(self, toolchain, project, tmpdir):

        setupTest(self, project, tmpdir)

        env = { TOOLCHAN_TO_ENVVAR[toolchain] : toolchain }
        cmdLine = ['build', '-B']
        assert runZm(self, cmdLine, env)[0] == 0
        assert "Autodetecting toolchain" not in self.zm['stdout']
        assert "Checking for '%s'" % toolchain in self.zm['stdout']

        checkBuildResults(self, cmdLine, True)
