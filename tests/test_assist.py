# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import pytest
from waflib.ConfigSet import ConfigSet
from waflib.Errors import WafError
import tests.common as cmn
from zm import assist, toolchains, utils
from zm.autodict import AutoDict
from zm.constants import *

joinpath = os.path.join

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

def testDumpZenMakeCommonFile(tmpdir):
    buildconffile = tmpdir.join("buildconf")
    buildconffile.write("buildconf")
    zmcmnfile = tmpdir.join("zmcmnfile")

    fakeConfPaths = AutoDict()
    fakeConfPaths.buildconffile = str(buildconffile)
    fakeConfPaths.zmcmnfile = str(zmcmnfile)

    assert not os.path.exists(fakeConfPaths.zmcmnfile)
    assist.dumpZenMakeCommonFile(fakeConfPaths)
    assert os.path.isfile(fakeConfPaths.zmcmnfile)

    cfgenv = ConfigSet(fakeConfPaths.zmcmnfile)
    assert 'monitfiles' in cfgenv
    assert cfgenv.monitfiles == [ fakeConfPaths.buildconffile ]
    assert 'monithash' in cfgenv

    _hash = 0
    for file in cfgenv.monitfiles:
        _hash = utils.mkHashOfStrings((_hash, utils.readFile(file, 'rb')))
    assert cfgenv.monithash == _hash

def testLoadTasksFromCache(tmpdir):
    cachefile = tmpdir.join("cachefile")
    assert assist.loadTasksFromCache(str(cachefile)) == {}
    cachedata = ConfigSet()
    cachedata.something = 11
    cachedata.store(str(cachefile))
    assert assist.loadTasksFromCache(str(cachefile)) == {}
    cachedata.alltasks = dict( a = 1, b =2 )
    cachedata.store(str(cachefile))
    assert assist.loadTasksFromCache(str(cachefile)) == cachedata.alltasks

def testMakeCacheConfFileName():
    name, zmcachedir = ('somename', 'somedir')
    path = assist.makeCacheConfFileName(zmcachedir, name)
    assert path == joinpath(zmcachedir, name + ZENMAKE_CACHE_NAMESUFFIX)

def testMakeTaskVariantName():
    buildtype = 'ddd'
    taskName = 'bbb'
    name = assist.makeTaskVariantName(buildtype, taskName)
    assert name == '%s.%s' % (buildtype, taskName)

    taskName = ' bbb '
    name = assist.makeTaskVariantName(buildtype, taskName)
    assert name == '%s.%s' % (buildtype, taskName.strip())

    taskName = ' bbb ccc '
    name = assist.makeTaskVariantName(buildtype, taskName)
    assert name == '%s.%s' % (buildtype, 'bbb_ccc')

    taskName = ' bbb ^$ccc '
    name = assist.makeTaskVariantName(buildtype, taskName)
    assert name == '%s.%s' % (buildtype, 'bbb_..ccc')

def testWriteWScriptFile(tmpdir):
    wscriptfile = tmpdir.join("wscript")
    assert not os.path.exists(str(wscriptfile))
    assist.writeWScriptFile(str(wscriptfile))
    assert os.path.exists(str(wscriptfile))
    with open(str(wscriptfile), 'r') as f:
        lines = f.readlines()
    found = [ x for x in lines if 'from zm.wscriptimpl import *' in x ]
    assert found

def testCopyEnv():
    rootenv = ConfigSet()
    rootenv.test1 = 'test1'
    childenv = rootenv.derive()
    childenv.test2 = 'test2'
    newenv = assist.copyEnv(childenv)
    assert childenv.test1 == 'test1'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'test1'
    assert newenv.test2 == 'test2'
    rootenv.test1 = 'abc'
    assert childenv.test1 == 'abc'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'abc'
    assert newenv.test2 == 'test2'
    childenv.test2 = 'dfg'
    assert childenv.test2 == 'dfg'
    assert newenv.test2 == 'test2'

def testDeepCopyEnv():
    rootenv = ConfigSet()
    rootenv.test1 = 'test1'
    childenv = rootenv.derive()
    childenv.test2 = 'test2'
    newenv = assist.deepcopyEnv(childenv)
    assert childenv.test1 == 'test1'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'test1'
    assert newenv.test2 == 'test2'
    rootenv.test1 = 'abc'
    assert childenv.test1 == 'abc'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'test1'
    assert newenv.test2 == 'test2'
    childenv.test2 = 'dfg'
    assert childenv.test2 == 'dfg'
    assert newenv.test2 == 'test2'

def testSetTaskEnvVars():
    cfgEnvVars = toolchains.CompilersInfo.allCfgEnvVars()

    taskParamsFixture = []
    for var in cfgEnvVars:
        taskParamsFixture.extend([
            { var.lower() : 'var1' },
            { var.lower() : 'var1 var2' },
            { var.lower() : ['var1', 'var2'] },
        ])

    for taskParams in taskParamsFixture:
        env = ConfigSet()
        assist.setTaskEnvVars(env, taskParams)
        for key, val in taskParams.items():
            envkey = key.upper()
            assert envkey in env
            assert env[envkey] == utils.toList(val)

def testDetectAllTaskFeatures():
    taskParams = {}
    assert assist.detectAllTaskFeatures(taskParams) == []

    taskParams = { 'features' : '' }
    assert assist.detectAllTaskFeatures(taskParams) == []

    taskParams = { 'run' : {} }
    assert assist.detectAllTaskFeatures(taskParams) == ['runcmd']

    for ftype in ('stlib', 'shlib', 'program'):
        for lang in ('c', 'cxx'):
            fulltype = '%s%s' % (lang, ftype)

            taskParams = { 'features' : fulltype }
            assert sorted(assist.detectAllTaskFeatures(taskParams)) == sorted([
                lang, fulltype
            ])

            taskParams = { 'features' : [lang, fulltype] }
            assert sorted(assist.detectAllTaskFeatures(taskParams)) == sorted([
                lang, fulltype
            ])

def testHandleTaskIncludesParam():

    taskParams = { 'features' : [] }
    includes = assist.handleTaskIncludesParam(taskParams, None)
    assert includes is None

    taskParams = { 'features' : ['cxx'] }
    srcroot = joinpath(os.getcwd(), 'testsrcroot') # just any abs path
    includes = assist.handleTaskIncludesParam(taskParams, srcroot)
    assert includes == ['.']

    taskParams = { 'features' : ['c'], 'includes': 'inc1 inc2' }
    includes = assist.handleTaskIncludesParam(taskParams, srcroot)
    assert includes == [
        joinpath(srcroot, taskParams['includes'].split()[0]),
        joinpath(srcroot, taskParams['includes'].split()[1]),
        '.'
    ]

    taskParams = { 'features' : ['cxx'], 'includes': ['inc1', 'inc2'] }
    includes = assist.handleTaskIncludesParam(taskParams, srcroot)
    assert includes == [
        joinpath(srcroot, taskParams['includes'][0]),
        joinpath(srcroot, taskParams['includes'][1]),
        '.'
    ]

    abspaths = [
        joinpath(os.getcwd(), '123', 'inc3'),
        joinpath(os.getcwd(), '456', 'inc4')]
    taskParams = { 'includes': abspaths, 'features' : ['c'], }
    includes = assist.handleTaskIncludesParam(taskParams, srcroot)
    assert includes == [ abspaths[0], abspaths[1], '.' ]

def testHandleTaskSourceParam(mocker):

    taskParams = {}
    srcDirNode = None
    src = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assert src == []

    # find with wildcard
    mockAttrs = { 'ant_glob.return_value' : 'wildcard' }
    srcDirNode = mocker.Mock(**mockAttrs)

    taskParams = { 'source' : dict( include = 'some/**/*.cpp' ), }
    rv = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assert rv == 'wildcard'
    taskParams = { 'source' : dict( include = 's/**/*.cpp', exclude = 'd/**/.cpp' ), }
    rv = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assert rv == 'wildcard'
    taskParams = { 'source' : dict( include = 's/**/*.cpp', ignorecase = True ), }
    rv = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assert rv == 'wildcard'

    calls = [
        mocker.call.ant_glob(incl = 'some/**/*.cpp', excl = '',
                ignorecase = False, remove = mocker.ANY),
        mocker.call.ant_glob(incl = 's/**/*.cpp', excl = 'd/**/.cpp',
                ignorecase = False, remove = mocker.ANY),
        mocker.call.ant_glob(incl = 's/**/*.cpp', excl = '',
                ignorecase = True, remove = mocker.ANY),
    ]

    assert srcDirNode.method_calls == calls

    # find as is
    mockAttrs = { 'find_node.side_effect' : ['foo', 'bar', 'baz'] }
    srcDirNode = mocker.Mock(**mockAttrs)
    taskParams = { 'source' : 'a.c', }
    rv = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assert rv == ['foo']
    taskParams = { 'source' : 'a.c b.c', }
    rv = assist.handleTaskSourceParam(taskParams, srcDirNode)
    assert rv == ['bar', 'baz']

    calls = [
        mocker.call.find_node('a.c'),
        mocker.call.find_node('a.c'),
        mocker.call.find_node('b.c'),
    ]

    assert srcDirNode.method_calls == calls

def testDistclean(tmpdir, monkeypatch):

    buildroot = tmpdir.mkdir("build")
    trashfile = buildroot.join("trash.txt")
    trashfile.write("content")
    projectroot = tmpdir.mkdir("project")
    trashfile = projectroot.join("trash2.txt")
    trashfile.write("content2")

    fakeConfPaths = AutoDict()
    fakeConfPaths.buildroot = str(buildroot.realpath())
    fakeConfPaths.realbuildroot = fakeConfPaths.buildroot
    fakeConfPaths.projectroot = str(projectroot.realpath())

    assert os.path.isdir(fakeConfPaths.buildroot)
    assert os.path.isdir(fakeConfPaths.projectroot)

    if PLATFORM != 'windows':
        buildsymlink = tmpdir.join("buildlink")
        buildsymlink.mksymlinkto(buildroot)
        fakeConfPaths.buildroot = str(buildsymlink)
        assert os.path.islink(fakeConfPaths.buildroot)

    lockfileName = 'testlockfile'
    lockfile = projectroot.join(lockfileName)
    lockfile.write("test lock")
    assert os.path.isfile(str(lockfile))

    from waflib import Options
    monkeypatch.setattr(Options, 'lockfile', lockfileName)

    wscriptfile = projectroot.join(WSCRIPT_NAME)
    wscriptfile.write("wscript")
    assert os.path.isfile(str(wscriptfile))

    with cmn.capturedOutput(): # just supress any output
        assist.distclean(fakeConfPaths)

    assert not os.path.exists(fakeConfPaths.realbuildroot)
    assert not os.path.exists(fakeConfPaths.buildroot)
    assert os.path.exists(fakeConfPaths.projectroot)
    assert not os.path.exists(str(wscriptfile))
    assert not os.path.exists(str(lockfile))

    # rare cases
    buildsymlink = tmpdir.mkdir("buildsymlink")
    fakeConfPaths.buildroot = str(buildsymlink)
    assert os.path.isdir(fakeConfPaths.buildroot)

    if PLATFORM != 'windows':
        somedir = tmpdir.mkdir("somedir")
        realbuildroot = tmpdir.join("buildroot")
        realbuildroot.mksymlinkto(somedir)
        fakeConfPaths.realbuildroot = str(realbuildroot)
        assert os.path.islink(fakeConfPaths.realbuildroot)

    with cmn.capturedOutput(): # just supress any output
        assist.distclean(fakeConfPaths)
    assert not os.path.exists(fakeConfPaths.realbuildroot)
    assert not os.path.exists(fakeConfPaths.buildroot)

def testIsBuildConfFake():
    fakeBuildConf = utils.loadPyModule('zm.buildconf.fakeconf', withImport = False)
    assert assist.isBuildConfFake(fakeBuildConf)

    # find first real buildconf.py and check
    prjdir = None
    for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
        if 'buildconf.py' in filenames:
            prjdir = dirpath
            break
    realBuildConf = utils.loadPyModule('buildconf', prjdir, withImport = False)
    assert not assist.isBuildConfFake(realBuildConf)

def testUsedWafTaskKeys():

    keys = set(assist.getUsedWafTaskKeys())
    assert 'features' in keys
    assist.registerUsedWafTaskKeys(['t1', 't2'])
    assert assist.getUsedWafTaskKeys() - set(['t1', 't2']) == keys

def testsSetConfDirectEnv():
    cfgCtx = AutoDict()
    name = 'something'
    env = dict(a = 321)
    assist.setConfDirectEnv(cfgCtx, name, env)
    assert cfgCtx.variant == name
    assert cfgCtx.all_envs[name] == env

def testRunConfTestsCheckPrograms(mocker):

    buildtype = 'buildtype'
    cfgCtx = getCfgCtxMock(mocker)
    tasks = AutoDict()
    tasks.task.conftests = [
        dict(act = 'check-programs', names = 'python2', mandatory = False),
        dict(act = 'check-programs', names = 'python2 python3', paths = '1 2')
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)

    calls = [
        mocker.call('python2', mandatory = False, path_list = mocker.ANY),
        mocker.call('python2', path_list = ['1', '2']),
        mocker.call('python3', path_list = ['1', '2']),
    ]

    assert cfgCtx.find_program.mock_calls == calls

def testRunConfTestsCheckSysLibs(mocker):

    buildtype = 'buildtype'
    cfgCtx = getCfgCtxMock(mocker)
    tasks = AutoDict()
    tasks.task['sys-libs'] = 'lib1 lib2'
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-sys-libs', mandatory = False),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)

    calls = [
        mocker.call(lib = 'lib1', mandatory = False),
        mocker.call(lib = 'lib2', mandatory = False),
    ]

    assert cfgCtx.check.mock_calls == calls

def testRunConfTestsCheckHeaders(mocker):

    buildtype = 'buildtype'
    cfgCtx = getCfgCtxMock(mocker)
    tasks = AutoDict()
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-headers', names = 'header1 header2', mandatory = False),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)

    calls = [
        mocker.call(header_name = 'header1', mandatory = False),
        mocker.call(header_name = 'header2', mandatory = False),
    ]

    assert cfgCtx.check.mock_calls == calls

def testRunConfTestsCheckLibs(mocker):

    buildtype = 'buildtype'
    cfgCtx = getCfgCtxMock(mocker)
    tasks = AutoDict()
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-libs', names = 'lib1 lib2', mandatory = False),
        dict(act = 'check-libs', names = 'lib3', autodefine = True),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)

    calls = [
        mocker.call(lib = 'lib1', mandatory = False),
        mocker.call(lib = 'lib2', mandatory = False),
        mocker.call(lib = 'lib3', define_name = 'HAVE_LIB_LIB3'),
    ]

    assert cfgCtx.check.mock_calls == calls

def testRunConfTestsWriteHeader(mocker):

    buildtype = 'buildtype'
    cfgCtx = getCfgCtxMock(mocker)
    tasks = AutoDict()
    tasks['some task']['$task.variant'] = buildtype
    tasks['some task'].conftests = [
        dict(act = 'write-config-header',),
        dict(act = 'write-config-header', file = 'file1'),
        dict(act = 'write-config-header', file = 'file2', guard = 'myguard'),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)

    calls = [
        mocker.call(joinpath(buildtype, 'some_task_config.h'),
                    guard = '_buildtype_some_task_config_h'.upper()),
        mocker.call(joinpath(buildtype, 'file1'),
                    guard = '_buildtype_file1'.upper()),
        mocker.call(joinpath(buildtype, 'file2'),
                    guard = 'myguard'),
    ]

    assert cfgCtx.write_config_header.mock_calls == calls

    cfgCtx = getCfgCtxMock(mocker)
    cfgCtx.setenv(buildtype)
    cfgCtx.env['PROJECT_NAME'] = 'test prj'

    assist.runConfTests(cfgCtx, buildtype, tasks)

    calls = [
        mocker.call(joinpath(buildtype, 'some_task_config.h'),
                    guard = 'test_prj_buildtype_some_task_config_h'.upper()),
        mocker.call(joinpath(buildtype, 'file1'),
                    guard = 'test_prj_buildtype_file1'.upper()),
        mocker.call(joinpath(buildtype, 'file2'),
                    guard = 'myguard'),
    ]

    assert cfgCtx.write_config_header.mock_calls == calls

def testRunConfTestsUnknown(mocker):

    buildtype = 'buildtype'
    cfgCtx = getCfgCtxMock(mocker)
    tasks = AutoDict()
    tasks.task.conftests = [
        dict(act = 'random act',),
    ]

    with pytest.raises(WafError):
        assist.runConfTests(cfgCtx, buildtype, tasks)

def testLoadToolchains(mocker):

    cfgCtx = getCfgCtxMock(mocker)
    cfgCtx.variant = 'old'

    bconfHandler = AutoDict()
    env = AutoDict()

    with pytest.raises(WafError):
        assist.loadToolchains(cfgCtx, bconfHandler, env)

    # load existing tools by name
    bconfHandler.customToolchains = {}
    bconfHandler.toolchainNames = ['gcc', 'g++', 'g++']
    toolchainsEnvs = assist.loadToolchains(cfgCtx, bconfHandler, env)
    for name in bconfHandler.toolchainNames:
        assert name in toolchainsEnvs
        assert toolchainsEnvs[name].loaded == 'loaded-' + name
    assert cfgCtx.variant == 'old'

    # auto load existing tool by lang
    bconfHandler.customToolchains = {}
    bconfHandler.toolchainNames = ['auto-c', 'auto-c++']
    toolchainsEnvs = assist.loadToolchains(cfgCtx, bconfHandler, env)
    assert toolchainsEnvs
    for name in bconfHandler.toolchainNames:
        assert name in toolchainsEnvs
        lang = name[5:]
        envVar = toolchains.CompilersInfo.varToSetCompiler(lang)
        compilers = toolchains.CompilersInfo.compilers(lang)
        assert envVar in toolchainsEnvs[name]
        assert toolchainsEnvs[name][envVar]

    assert cfgCtx.variant == 'old'

    # load custom tool
    bconfHandler.customToolchains = {
        'local-g++': AutoDict({
            'kind' : 'g++',
            'vars' : { 'CXX' : 'some_path/g++'} ,
        })
    }
    bconfHandler.toolchainNames = ['local-g++', 'g++']
    toolchainsEnvs = assist.loadToolchains(cfgCtx, bconfHandler, env)
    assert toolchainsEnvs['g++'].loaded == 'loaded-g++'
    assert toolchainsEnvs['local-g++'].loaded == 'loaded-g++'
    assert cfgCtx.variant == 'old'

    # errors
    cfgCtx.load = mocker.MagicMock(side_effect = WafError)
    bconfHandler.customToolchains = {}
    bconfHandler.toolchainNames = ['auto-c', 'auto-c++']
    with pytest.raises(WafError):
        assist.loadToolchains(cfgCtx, bconfHandler, env)
