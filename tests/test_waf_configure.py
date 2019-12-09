# coding=utf-8
#

# _pylint: skip-file
# pylint: disable = wildcard-import, unused-wildcard-import, unused-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = no-member, redefined-outer-name

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import pytest

from waflib import Context, Options
from waflib.ConfigSet import ConfigSet
from waflib.Errors import WafError
import tests.common as cmn
from zm.autodict import AutoDict
from zm import toolchains, utils, log
from zm.waf import context, configure
from zm.waf.configure import ConfigurationContext

joinpath = os.path.join

class FakeConfig(object):

    def __init__(self):
        self.projectName = ''

@pytest.fixture
def cfgctx(monkeypatch, mocker):
    monkeypatch.setattr(Options, 'options', AutoDict())
    cfgCtx = ConfigurationContext(run_dir = os.getcwd())
    setattr(cfgCtx, 'fakebconf', FakeConfig())

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

    def getbconf():
        return cfgCtx.fakebconf
    cfgCtx.getbconf = mocker.MagicMock(side_effect = getbconf)

    def load(toolchain):
        self = cfgCtx
        env = self.all_envs[cfgCtx.variant]
        for lang in ('c', 'c++'):
            compilers = toolchains.CompilersInfo.compilers(lang)
            envVar    = toolchains.CompilersInfo.varToSetCompiler(lang)
            if toolchain in compilers:
                env[envVar] = ['/usr/bin/%s' % toolchain]
        env.loaded = 'loaded-' + toolchain

    cfgCtx.load = mocker.MagicMock(side_effect = load)

    cfgCtx.start_msg = mocker.MagicMock()
    cfgCtx.end_msg = mocker.MagicMock()

    return cfgCtx

def getCfgCtxMock(mocker):

    cfgCtx = mocker.MagicMock(all_envs = {})
    self = cfgCtx
    cfgCtx.fatal = mocker.MagicMock(side_effect = WafError)

    def setenv(name, env = None):
        self.variant = name
        if name not in self.all_envs or env:
            if not env:
                env = ConfigSet()
            else:
                env = env.derive()
            self.all_envs[name] = env

    cfgCtx.setenv = mocker.MagicMock(side_effect = setenv)

    def envProp(val = None):
        if val is not None:
            self.all_envs[self.variant] = val
        return self.all_envs[self.variant]

    type(cfgCtx).env = mocker.PropertyMock(side_effect = envProp)

    def load(toolchain):
        self = cfgCtx
        env = self.all_envs[cfgCtx.variant]
        for lang in ('c', 'c++'):
            compilers = toolchains.CompilersInfo.compilers(lang)
            envVar    = toolchains.CompilersInfo.varToSetCompiler(lang)
            if toolchain in compilers:
                env[envVar] = ['/usr/bin/%s' % toolchain]
        env.loaded = 'loaded-' + toolchain

    cfgCtx.load = mocker.MagicMock(side_effect = load)

    return cfgCtx

def testsSetDirectEnv(cfgctx):
    ctx = cfgctx
    name = 'something'
    env = dict(a = 321)
    ctx.setDirectEnv(name, env)
    assert ctx.variant == name
    assert ctx.all_envs[name] == env

def testRunConfTestsCheckPrograms(mocker, cfgctx):

    mocker.patch('zm.log.info')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task.conftests = [
        dict(act = 'check-programs', names = 'python2', mandatory = False),
        dict(act = 'check-programs', names = 'python2 python3', paths = '1 2')
    ]

    ctx.find_program = mocker.MagicMock()
    ctx.runConfTests(buildtype, tasks)

    calls = [
        mocker.call('python2', mandatory = False, path_list = mocker.ANY),
        mocker.call('python2', path_list = ['1', '2']),
        mocker.call('python3', path_list = ['1', '2']),
    ]

    assert ctx.find_program.mock_calls == calls

def testRunConfTestsCheckSysLibs(mocker, cfgctx):

    mocker.patch('zm.log.info')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task['sys-libs'] = 'lib1 lib2'
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-sys-libs', mandatory = False),
    ]

    ctx.check = mocker.MagicMock()
    ctx.runConfTests(buildtype, tasks)

    calls = [
        mocker.call(lib = 'lib1', mandatory = False, msg = mocker.ANY),
        mocker.call(lib = 'lib2', mandatory = False, msg = mocker.ANY),
    ]

    assert ctx.check.mock_calls == calls

def testRunConfTestsCheckHeaders(mocker, cfgctx):

    mocker.patch('zm.log.info')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-headers', names = 'header1 header2', mandatory = False),
    ]

    ctx.check = mocker.MagicMock()
    ctx.runConfTests(buildtype, tasks)

    calls = [
        mocker.call(header_name = 'header1', mandatory = False, msg = mocker.ANY),
        mocker.call(header_name = 'header2', mandatory = False, msg = mocker.ANY),
    ]

    assert ctx.check.mock_calls == calls

def testRunConfTestsCheckLibs(mocker, cfgctx):

    mocker.patch('zm.log.info')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-libs', names = 'lib1 lib2', mandatory = False),
        dict(act = 'check-libs', names = 'lib3', autodefine = True),
    ]

    ctx.check = mocker.MagicMock()
    ctx.runConfTests(buildtype, tasks)

    msg = mocker.ANY
    calls = [
        mocker.call(lib = 'lib1', mandatory = False, msg = msg),
        mocker.call(lib = 'lib2', mandatory = False, msg = msg),
        mocker.call(lib = 'lib3', define_name = 'HAVE_LIB_LIB3', msg = msg),
    ]

    assert ctx.check.mock_calls == calls

def testRunConfTestsWriteHeader(mocker, cfgctx):

    mocker.patch('zm.log.info')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks['some task']['$task.variant'] = buildtype
    tasks['some task'].conftests = [
        dict(act = 'write-config-header',),
        dict(act = 'write-config-header', file = 'file1'),
        dict(act = 'write-config-header', file = 'file2', guard = 'myguard'),
    ]

    ctx.write_config_header = mocker.MagicMock()
    ctx.runConfTests(buildtype, tasks)

    calls = [
        mocker.call(joinpath(buildtype, 'some_task_config.h'), top = True,
                    guard = '_buildtype_some_task_config_h'.upper()),
        mocker.call(joinpath(buildtype, 'file1'), top = True,
                    guard = '_buildtype_file1'.upper()),
        mocker.call(joinpath(buildtype, 'file2'), top = True,
                    guard = 'myguard'),
    ]

    assert ctx.write_config_header.mock_calls == calls

    ctx.fakebconf.projectName = 'test prj'
    ctx.write_config_header.reset_mock()
    ctx.runConfTests(buildtype, tasks)

    calls = [
        mocker.call(joinpath(buildtype, 'some_task_config.h'), top = True,
                    guard = 'test_prj_buildtype_some_task_config_h'.upper()),
        mocker.call(joinpath(buildtype, 'file1'), top = True,
                    guard = 'test_prj_buildtype_file1'.upper()),
        mocker.call(joinpath(buildtype, 'file2'), top = True,
                    guard = 'myguard'),
    ]

    assert ctx.write_config_header.mock_calls == calls

def testRunConfTestsUnknown(mocker, cfgctx):

    mocker.patch('zm.log.info')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task.conftests = [
        dict(act = 'random act',),
    ]

    with pytest.raises(WafError):
        ctx.runConfTests(buildtype, tasks)

def testLoadToolchains(mocker, cfgctx):

    ctx = cfgctx
    ctx.variant = 'old'

    bconf = AutoDict()
    env = AutoDict()

    #with pytest.raises(WafError):
    #    ctx.loadToolchains(bconf, env)

    # load existing tools by name
    bconf.customToolchains = {}
    bconf.toolchainNames = ['gcc', 'g++', 'g++']
    toolchainsEnvs = ctx.loadToolchains(bconf, env)
    for name in bconf.toolchainNames:
        assert name in toolchainsEnvs
        assert toolchainsEnvs[name].loaded == 'loaded-' + name
    assert ctx.variant == 'old'

    # auto load existing tool by lang
    bconf.customToolchains = {}
    bconf.toolchainNames = ['auto-c', 'auto-c++']
    toolchainsEnvs = ctx.loadToolchains(bconf, env)
    assert toolchainsEnvs
    for name in bconf.toolchainNames:
        assert name in toolchainsEnvs
        lang = name[5:]
        envVar = toolchains.CompilersInfo.varToSetCompiler(lang)
        #compilers = toolchains.CompilersInfo.compilers(lang)
        assert envVar in toolchainsEnvs[name]
        assert toolchainsEnvs[name][envVar]

    assert ctx.variant == 'old'

    # load custom tool
    bconf.customToolchains = {
        'local-g++': AutoDict({
            'kind' : 'g++',
            'vars' : { 'CXX' : 'some_path/g++'} ,
        })
    }
    bconf.toolchainNames = ['local-g++', 'g++']
    toolchainsEnvs = ctx.loadToolchains(bconf, env)
    assert toolchainsEnvs['g++'].loaded == 'loaded-g++'
    assert toolchainsEnvs['local-g++'].loaded == 'loaded-g++'
    assert ctx.variant == 'old'

    # errors
    ctx.zmcache().clear()
    ctx.load = mocker.MagicMock(side_effect = WafError)
    bconf.customToolchains = {}
    bconf.toolchainNames = ['auto-c', 'auto-c++']
    with pytest.raises(WafError):
        ctx.loadToolchains(bconf, env)
