# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import types
import platform as _platform
import pytest

from zm import pyutils
from zm.autodict import AutoDict
from zm.buildconf import loader as bconfloader

@pytest.fixture(scope = "session", autouse = True)
def beforeAllTests(request):
    # Additional check for pyenv
    if 'PYENV_VERSION' in os.environ:
        realVersion = _platform.python_version()
        envVersion = os.environ['PYENV_VERSION']
        assert envVersion in (realVersion, 'system')

@pytest.fixture
def unsetEnviron(monkeypatch):
    from zm.waf.assist import getMonitoredEnvVarNames
    varnames = getMonitoredEnvVarNames()
    for v in varnames:
        #os.environ.pop(v, None)
        monkeypatch.delenv(v, raising = False)

@pytest.fixture
def testingBuildConf():
    buildconf = types.ModuleType('buildconf')
    buildconf.__file__ = os.path.abspath('buildconf.py')
    bconfloader.applyDefaults(buildconf, True, os.path.dirname(buildconf.__file__))

    # AutoDict is more useful in tests

    for k, v in vars(buildconf).items():
        if isinstance(v, pyutils.maptype):
            setattr(buildconf, k, AutoDict(v))

    return AutoDict(vars(buildconf))

def pytest_report_header(config):
    from zm.waf import wrappers
    from zm import sysinfo
    sysinfo.printSysInfo()
    return ""

@pytest.hookimpl(hookwrapper = True, tryfirst = True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)
