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
from copy import deepcopy
import pytest

from waflib import Context, Options, Build
from waflib.ConfigSet import ConfigSet
from waflib.Errors import WafError
from zm.autodict import AutoDict
from zm import toolchains, utils, log
from zm.error import *
from zm.waf import context, configure, assist
from zm.buildconf.processing import Config as BuildConfig
from zm.waf.configure import ConfigurationContext
from zm.features import ToolchainVars, c, cxx
from tests.common import asRealConf

joinpath = os.path.join

class FakeConfig(object):

    def __init__(self):
        self.projectName = ''

@pytest.fixture
def cfgctx(monkeypatch, mocker, tmpdir):

    rundir = str(tmpdir.realpath())
    outdir = joinpath(rundir, 'out')

    monkeypatch.setattr(Context, 'launch_dir', rundir)
    monkeypatch.setattr(Context, 'run_dir', rundir)
    monkeypatch.setattr(Context, 'out_dir', outdir)

    monkeypatch.chdir(Context.run_dir)

    monkeypatch.setattr(Options, 'options', AutoDict())
    cfgCtx = ConfigurationContext(run_dir = rundir)

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

    def getbconf(pathNode):
        return cfgCtx.fakebconf
    cfgCtx.getbconf = mocker.MagicMock(side_effect = getbconf)

    def loadTool(toolchain, **kwargs):
        # pylint: disable = unused-argument
        self = cfgCtx
        env = self.all_envs[cfgCtx.variant]
        for lang in ('c', 'cxx'):
            compilers = toolchains.getNames(lang)
            envVar    = ToolchainVars.sysVarToSetToolchain(lang)
            if toolchain in compilers:
                env[envVar] = ['/usr/bin/%s' % toolchain]
        env.loaded = 'loaded-' + toolchain
        return env

    cfgCtx.loadTool = mocker.MagicMock(side_effect = loadTool)

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

def prepareCfgTasks(ctx):
    ctx.mergeTasks()
    ctx.allOrderedTasks = assist.orderTasksByLocalDeps(ctx.allTasks)

def testsSetDirectEnv(cfgctx):
    ctx = cfgctx
    name = 'something'
    env = dict(a = 321)
    ctx.setDirectEnv(name, env)
    assert ctx.variant == name
    assert ctx.all_envs[name] == env

def testRunConfigActionsFindProgram(mocker, cfgctx):

    mocker.patch('zm.log.info')
    mocker.patch('zm.log.warn')

    ctx = cfgctx
    tasks = AutoDict()
    tasks.task.name = 'task'
    tasks.task.features = ['c', 'cshlib']
    tasks.task['configure'] = [
        dict(do = 'find-program', names = 'python2', mandatory = False),
        dict(do = 'find-program', names = 'python2 python3', paths = '1 2')
    ]
    tasks.task['$task.variant'] = 'test'

    ctx.bconfManager = AutoDict(configs = [AutoDict(tasks = tasks)])
    prepareCfgTasks(ctx)

    ctx.find_program = mocker.MagicMock(return_value = 'path')
    ctx.runConfigActions()

    ignoreArgs = { k: mocker.ANY for k in ['var'] }

    calls = [
        mocker.call(['python2'], mandatory = False, path_list = mocker.ANY, **ignoreArgs),
        mocker.call(['python2', 'python3'], path_list = ['1', '2'], **ignoreArgs),
    ]

    assert ctx.find_program.mock_calls == calls

def testRunConfigActionsCheckSysLibs(mocker, cfgctx):

    mocker.patch('zm.log.info')
    mocker.patch('zm.log.warn')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task.name = 'task'
    tasks.task.features = ['cxx', 'cxxshlib']
    tasks.task['libs'] = 'lib1 lib2'
    tasks.task['$task.variant'] = buildtype
    tasks.task['$tlang'] = 'cxx'
    tasks.task['configure'] = [
        dict(do = 'check-libs', fromtask = True, mandatory = False),
    ]

    ctx.bconfManager = AutoDict(configs = [AutoDict(tasks = tasks)])
    prepareCfgTasks(ctx)

    ctx.check = mocker.MagicMock()
    ctx.runConfigActions()

    ignoreArgs = ['msg', '$conf-test-hash', 'type', 'compile_filename',
                  'code', 'compile_mode', 'add_have_to_env', 'saved-result-args']
    ignoreArgs = { k: mocker.ANY for k in ignoreArgs }

    calls = [
        mocker.call(lib = 'lib1', mandatory = False, compiler = 'cxx', **ignoreArgs),
        mocker.call(lib = 'lib2', mandatory = False, compiler = 'cxx', **ignoreArgs),
    ]

    assert ctx.check.mock_calls == calls

def testRunConfigActionsCheckHeaders(mocker, cfgctx):

    mocker.patch('zm.log.info')
    mocker.patch('zm.log.warn')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task.name = 'task'
    tasks.task.features = ['c', 'cshlib']
    tasks.task['$task.variant'] = buildtype
    tasks.task['$tlang'] = 'c'
    tasks.task['configure'] = [
        dict(do = 'check-headers', names = 'header1 header2', mandatory = False),
    ]

    ctx.bconfManager = AutoDict(configs = [AutoDict(tasks = tasks)])
    prepareCfgTasks(ctx)

    ctx.check = mocker.MagicMock()
    ctx.runConfigActions()

    ignoreArgs = ['msg', '$conf-test-hash', 'type', 'compile_filename',
                  'code', 'compile_mode', 'add_have_to_env', 'saved-result-args']
    ignoreArgs = { k: mocker.ANY for k in ignoreArgs }

    calls = [
        mocker.call(header_name = 'header1', mandatory = False,
                    compiler = 'c', **ignoreArgs),
        mocker.call(header_name = 'header2', mandatory = False,
                    compiler = 'c', **ignoreArgs),
    ]

    assert ctx.check.mock_calls == calls

def testRunConfigActionsCheckLibs(mocker, cfgctx):

    mocker.patch('zm.log.info')
    mocker.patch('zm.log.warn')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks.task.name = 'task'
    tasks.task.features = ['c', 'cshlib']
    tasks.task['$task.variant'] = buildtype
    tasks.task['$tlang'] = 'c'
    tasks.task['configure'] = [
        dict(do = 'check-libs', names = 'lib1 lib2', mandatory = False),
        dict(do = 'check-libs', names = 'lib3', autodefine = True),
    ]

    ctx.bconfManager = AutoDict(configs = [AutoDict(tasks = tasks)])
    prepareCfgTasks(ctx)

    ctx.check = mocker.MagicMock()
    ctx.runConfigActions()

    ignoreArgs = ['msg', '$conf-test-hash', 'type', 'compile_filename',
                  'code', 'compile_mode', 'add_have_to_env', 'saved-result-args']
    ignoreArgs = { k: mocker.ANY for k in ignoreArgs }

    calls = [
        mocker.call(lib = 'lib1', mandatory = False,
                    compiler = 'c', **ignoreArgs),
        mocker.call(lib = 'lib2', mandatory = False,
                    compiler = 'c', **ignoreArgs),
        mocker.call(lib = 'lib3', define_name = 'HAVE_LIB_LIB3',
                    compiler = 'c', **ignoreArgs),
    ]

    assert ctx.check.mock_calls == calls

def testRunConfigActionsWriteHeader(mocker, cfgctx):

    mocker.patch('zm.log.info')
    mocker.patch('zm.log.warn')

    ctx = cfgctx
    buildtype = 'buildtype'
    tasks = AutoDict()
    tasks['some task'].name = 'some task'
    tasks['some task'].features = ['c', 'cshlib']
    tasks['some task']['$task.variant'] = buildtype
    tasks['some task']['$tlang'] = 'c'
    tasks['some task']['configure'] = [
        { 'do' : 'write-config-header', },
        { 'do' : 'write-config-header', 'file' : 'file1' },
        { 'do' : 'write-config-header', 'file' : 'file2', 'guard' : 'myguard' },
        { 'do' : 'write-config-header', 'file' : 'file1', 'remove-defines' : False },
    ]
    ctx.fakebconf.tasks = tasks
    ctx.fakebconf.selectedBuildType = buildtype

    ctx.bconfManager = AutoDict(configs = [ctx.fakebconf])
    ctx.bconfManager.root = ctx.fakebconf
    prepareCfgTasks(ctx)

    ctx.write_config_header = mocker.MagicMock()
    ctx.runConfigActions()

    calls = [
        mocker.call(joinpath(buildtype, 'some_task_config.h'), top = True,
                    guard = '_buildtype_some_task_config_h'.upper(), remove = True),
        mocker.call(joinpath(buildtype, 'file1'), top = True,
                    guard = '_buildtype_file1'.upper(), remove = True),
        mocker.call(joinpath(buildtype, 'file2'), top = True,
                    guard = 'myguard', remove = True),
        mocker.call(joinpath(buildtype, 'file1'), top = True,
                    guard = '_buildtype_file1'.upper(), remove = False),
    ]

    assert ctx.write_config_header.mock_calls == calls

    ctx.fakebconf.projectName = 'test prj'
    ctx.write_config_header.reset_mock()
    ctx.runConfigActions()

    calls = [
        mocker.call(joinpath(buildtype, 'some_task_config.h'), top = True,
                    guard = 'test_prj_buildtype_some_task_config_h'.upper(), remove = True),
        mocker.call(joinpath(buildtype, 'file1'), top = True,
                    guard = 'test_prj_buildtype_file1'.upper(), remove = True),
        mocker.call(joinpath(buildtype, 'file2'), top = True,
                    guard = 'myguard', remove = True),
        mocker.call(joinpath(buildtype, 'file1'), top = True,
                    guard = 'test_prj_buildtype_file1'.upper(), remove = False),
    ]

    assert ctx.write_config_header.mock_calls == calls

def testRunConfigActionsUnknown(mocker, cfgctx):

    mocker.patch('zm.log.info')
    mocker.patch('zm.log.warn')

    ctx = cfgctx
    tasks = AutoDict()
    tasks.task.name = 'task'
    tasks.task.features = ['c', 'cshlib']
    tasks.task['configure'] = [
        dict(do = 'random act',),
    ]
    tasks.task['$task.variant'] = 'test'

    ctx.bconfManager = AutoDict(configs = [AutoDict(tasks = tasks)])
    prepareCfgTasks(ctx)

    with pytest.raises(WafError):
        ctx.runConfigActions()

def _checkToolchainNames(ctx, buildconf, buildtype, expected):
    bconf = BuildConfig(asRealConf(buildconf))
    bconf.applyBuildType(buildtype)
    assert sorted(ctx.handleToolchains(bconf)) == sorted(expected)

def testToolchainNames(testingBuildConf, cfgctx, monkeypatch):

    ctx = cfgctx

    buildconf = testingBuildConf

    # CASE: invalid use
    bconf = BuildConfig(asRealConf(buildconf))
    with pytest.raises(ZenMakeLogicError):
        _ = ctx.handleToolchains(bconf)

    buildconf.buildtypes['debug-gxx'] = {}
    buildconf.buildtypes.default = 'debug-gxx'
    buildtype = 'debug-gxx'

    # CASE: just empty toolchains
    buildconf = deepcopy(testingBuildConf)
    buildconf.tasks.test1.param1 = '111'
    buildconf.tasks.test2.param2 = '222'
    bconf = BuildConfig(asRealConf(buildconf))
    bconf.applyBuildType(buildtype)
    # it returns tuple but it can return list so we check by len
    assert len(ctx.handleToolchains(bconf)) == 0

    # CASE: tasks with the same toolchain
    buildconf = deepcopy(testingBuildConf)
    buildconf.tasks.test1.toolchain = 'gxx'
    buildconf.tasks.test2.toolchain = 'gxx'
    _checkToolchainNames(ctx, buildconf, buildtype, ['gxx'])

    # CASE: tasks with different toolchains
    buildconf = deepcopy(testingBuildConf)
    buildconf.tasks.test1.toolchain = 'gxx'
    buildconf.tasks.test2.toolchain = 'lgxx'
    _checkToolchainNames(ctx, buildconf, buildtype, ['gxx', 'lgxx'])

    # CASE: toolchain from system env
    buildconf = deepcopy(testingBuildConf)
    buildconf.tasks.test1.toolchain = 'gxx'
    buildconf.tasks.test1.features = ['c']
    for tool in ('clang', 'gcc'):
        monkeypatch.setenv('CC', tool)
        _checkToolchainNames(ctx, buildconf, buildtype, [tool])
        monkeypatch.delenv('CC')

    ### byfilter

    # CASE: empty toolchains in byfilter
    buildconf = deepcopy(testingBuildConf)
    buildconf.byfilter = [
        {
            'for' : { 'task' : 'test1' },
            'set' : { 'param1' : '11', 'param2' : '22' }
        },
    ]
    bconf = BuildConfig(asRealConf(buildconf))
    bconf.applyBuildType(buildtype)
    # it returns tuple but it can return list so we check by len
    assert len(ctx.handleToolchains(bconf)) == 0

    # CASE: tasks in byfilter with the same toolchain
    buildconf = deepcopy(testingBuildConf)
    buildconf.byfilter = [
        { 'for' : { 'task' : 'test1' }, 'set' : { 'toolchain' : 'gxx' } },
        { 'for' : { 'task' : 'test2' }, 'set' : { 'toolchain' : 'gxx' } },
    ]
    _checkToolchainNames(ctx, buildconf, buildtype, ['gxx'])

    # CASE: tasks in byfilter with the different toolchains
    buildconf = deepcopy(testingBuildConf)
    buildconf.byfilter = [
        { 'for' : { 'task' : 'test1' }, 'set' : { 'toolchain' : 'gxx' } },
        { 'for' : { 'task' : 'test2' }, 'set' : { 'toolchain' : 'lgxx' } },
    ]
    _checkToolchainNames(ctx, buildconf, buildtype, ['gxx', 'lgxx'])

def _setToolchains(ctx, bconf, toolchainNames):
    ctx.validToolchainNames = set(toolchainNames)
    ctx.validToolchainNames.update(set(bconf.customToolchains.keys()))
    bconf.tasks = AutoDict()
    for i, name in enumerate(toolchainNames):
        bconf.tasks['task%d' % i].toolchain = name

def testLoadToolchains(cfgctx):

    ctx = cfgctx
    ctx.variant = 'old'

    bconf = AutoDict()

    # load existing tools by name
    toolchainNames = ['gcc', 'g++', 'g++']
    _setToolchains(ctx, bconf, toolchainNames)
    bconf.customToolchains = AutoDict()
    toolchainsEnvs = ctx.loadToolchains(bconf)
    for name in toolchainNames:
        assert name in toolchainsEnvs
        assert toolchainsEnvs[name].loaded == 'loaded-' + name
    assert ctx.variant == 'old'

    # auto load existing tool by lang
    bconf.customToolchains = AutoDict()
    toolchainNames = ['auto-c', 'auto-c++']
    _setToolchains(ctx, bconf, toolchainNames)
    toolchainsEnvs = ctx.loadToolchains(bconf)
    assert toolchainsEnvs
    for name in toolchainNames:
        assert name in toolchainsEnvs
        lang = name[5:].replace('+', 'x')
        envVar = ToolchainVars.sysVarToSetToolchain(lang)
        assert envVar in toolchainsEnvs[name]
        assert toolchainsEnvs[name][envVar]

    assert ctx.variant == 'old'

    # load custom tool
    bconf.customToolchains = AutoDict({
        'local-g++': AutoDict({
            'kind' : 'g++',
            'vars' : { 'CXX' : 'some_path/g++'} ,
        })
    })
    toolchainNames = ['local-g++', 'g++']
    _setToolchains(ctx, bconf, toolchainNames)
    toolchainsEnvs = ctx.loadToolchains(bconf)
    assert toolchainsEnvs['g++'].loaded == 'loaded-g++'
    assert toolchainsEnvs['local-g++'].loaded == 'loaded-g++'
    assert ctx.variant == 'old'

def testLoadToolchainsErrors(mocker, cfgctx):

    ctx = cfgctx
    bconf = AutoDict()

    ctx.loadTool = mocker.MagicMock(side_effect = WafError)
    bconf.customToolchains = AutoDict()
    bconf.toolchainNames = ['auto-c', 'auto-c++']
    _setToolchains(ctx, bconf, ['local-g++', 'g++'])
    with pytest.raises(WafError):
        ctx.loadToolchains(bconf)
