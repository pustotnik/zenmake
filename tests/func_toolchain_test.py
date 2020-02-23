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
        dict( default = ('linux', 'darwin'), travis = ('darwin'), ),
    ('ldc2', joinpath('d', '02-withlibs')) :
        dict( default = ('linux', 'darwin'), travis = ('linux', 'darwin'), ),
    ('gdc', joinpath('d', '02-withlibs')) :
        dict( default = ('linux', 'darwin'), travis = ('linux'), ),
}

def _generateParams():

    params = []

    isTravisCI = os.environ.get('TRAVIS', None) == 'true' and \
                    os.environ.get('CI', None) == 'true'

    disableGDC = False

    # Due to bug with packages ldc + gdc:
    # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=827211
    if isTravisCI and PLATFORM == 'linux':
        travisDist = os.environ.get('TRAVIS_DIST', '')
        disableGDC = travisDist == 'xenial'

    for item, condition in PARAMS_CONFIG.items():
        condition = condition['travis'] if isTravisCI else condition['default']
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
