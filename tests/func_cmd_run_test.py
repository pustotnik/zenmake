# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = unused-argument, attribute-defined-outside-init

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import pytest
from zm.constants import PLATFORM

from tests.func_utils import *

PARAMS_CONFIG = [
    [joinpath('cpp', '09-complex-unittest'), ['', 'complex'],
        '', "The program has finished"],
    [joinpath('c', '07-with spaces'), ['my test', 'my test alt'],
        '', "The demo 'with spaces' has finished"],
    [joinpath('c', '07-with spaces'), ['my test', 'my test alt'],
        'some-arg', "The command line argument supplied is 'some-arg'"],
]

def _generateParams():

    params = []
    for item in PARAMS_CONFIG:
        toRun = item[1]
        if PLATFORM == 'windows':
            toRun += [x + '.exe' for x in toRun if x]
        for target in toRun:
            cliargs = [target] if target else []
            if item[2]:
                cliargs += ['--', item[2]]
            _item = [item[0], cliargs, item[3]]
            idstr = _item[0] + ':' + target
            if len(cliargs) > 1:
                idstr += ' (cli arg)'
            params.append(pytest.param(*_item, id = idstr))

    return params

@pytest.mark.usefixtures("unsetEnviron")
class TestCmdRun(object):

    @pytest.fixture(params = getZmExecutables(), autouse = True)
    def allZmExe(self, request):
        self.zmExe = zmExes[request.param]

    @pytest.fixture
    def project(self, request, tmpdir):

        def teardown():
            printErrorOnFailed(self, request)

        request.addfinalizer(teardown)
        return setupTest(self, request, tmpdir)

    # https://docs.pytest.org/en/latest/example/parametrize.html#apply-indirect-on-particular-arguments
    @pytest.mark.parametrize(
        "project, cliargs, checkstring",
        _generateParams(), indirect=["project"]
    )
    def testMain(self, project, cliargs, checkstring):

        cmdLine = ['run']
        if cliargs:
            cmdLine += cliargs

        returncode, stdout, _ = runZm(self, cmdLine)
        assert returncode == 0
        assert stdout

        # There is a problem with incorrect order of messages in stdout from programs
        # on Windows. If such a program uses printf function in libraries and
        # you use pipes (Popen) to communicate with stdout from this program then
        # order of messages will be incorrect.
        # The runZm function uses pipes to capture stdout.
        # At the moment I don't know how to fix it without modification of code
        # of the demo programs (setbuf(stdout, NULL) can be used for example)
        # that are used for curent test.
        lastLines = stdout.splitlines()[-10:]
        assert checkstring in lastLines
