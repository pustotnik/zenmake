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

joinpath = os.path.join

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

@pytest.fixture
def cfgctx(monkeypatch, mocker, tmpdir):

    from waflib import Context, Options, Build
    from waflib.ConfigSet import ConfigSet
    from waflib.Errors import WafError
    from zm.waf.configure import ConfigurationContext

    rundir = str(tmpdir.realpath())
    outdir = joinpath(rundir, 'out')

    monkeypatch.setattr(Context, 'launch_dir', rundir)
    monkeypatch.setattr(Context, 'run_dir', rundir)
    monkeypatch.setattr(Context, 'out_dir', outdir)

    monkeypatch.chdir(Context.run_dir)

    monkeypatch.setattr(Options, 'options', AutoDict())
    cfgCtx = ConfigurationContext(run_dir = rundir)

    cfgCtx.fatal = mocker.MagicMock(side_effect = WafError)

    def setenv(name, env = None):
        cfgCtx.variant = name
        if name not in cfgCtx.all_envs or env:
            if not env:
                env = ConfigSet()
            else:
                env = env.derive()
            cfgCtx.all_envs[name] = env

    cfgCtx.setenv = mocker.MagicMock(side_effect = setenv)

    def envProp(val = None):
        if val is not None:
            cfgCtx.all_envs[cfgCtx.variant] = val
        return cfgCtx.all_envs[cfgCtx.variant]

    type(cfgCtx).env = mocker.PropertyMock(side_effect = envProp)

    cfgCtx.start_msg = cfgCtx.startMsg = mocker.MagicMock()
    cfgCtx.end_msg = cfgCtx.endMsg = mocker.MagicMock()
    cfgCtx.to_log = mocker.MagicMock()

    cfgCtx.top_dir = rundir
    cfgCtx.out_dir = outdir
    cfgCtx.init_dirs()
    assert cfgCtx.srcnode.abspath().startswith(rundir)
    assert cfgCtx.bldnode.abspath().startswith(rundir)
    cfgCtx.top_dir = None
    cfgCtx.out_dir = None

    cfgCtx.cachedir = cfgCtx.bldnode.make_node(Build.CACHE_DIR)
    cfgCtx.cachedir.mkdir()

    cfgCtx.loadCaches()

    return cfgCtx
