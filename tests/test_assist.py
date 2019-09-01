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

class MockCfgCtx(object):
    def __init__(self):
        self.all_envs = {}
        self.setenv('')
        self.calls = []

    def setenv(self, name, env = None):
        self.variant = name
        if name not in self.all_envs or env:
            if not env:
                env = AutoDict()
            self.all_envs[name] = env

    def getEnv(self):
        return self.all_envs[self.variant]
    def setEnv(self, val):
        self.all_envs[self.variant] = val
    env = property(getEnv, setEnv)

    def find_program(self, filename, **kw):
        self.calls.append( dict( func = 'find_program',
                            args = [filename, kw] ) )

    def write_config_header(self, filename, **kw):
        self.calls.append( dict( func = 'write_config_header',
                            args = [filename, kw] ) )

    def check(self, **kw):
        self.calls.append( dict( func = 'check', args = kw ) )

    def fatal(self, msg, ex = None):
        raise WafError(msg, ex=ex)

def testRunConfTestsCheckPrograms():

    buildtype = 'buildtype'
    cfgCtx = MockCfgCtx()
    tasks = AutoDict()
    tasks.task.conftests = [
        dict(act = 'check-programs', names = 'python2', mandatory = False),
        dict(act = 'check-programs', names = 'python2 python3', paths = '1 2')
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)
    call = cfgCtx.calls[0]
    assert call['func'] == 'find_program'
    assert call['args'][0] == 'python2'
    assert call['args'][1]['mandatory'] == False
    call = cfgCtx.calls[1]
    assert call['func'] == 'find_program'
    assert call['args'][0] == 'python2'
    assert call['args'][1]['path_list'] == ['1', '2']
    call = cfgCtx.calls[2]
    assert call['func'] == 'find_program'
    assert call['args'][0] == 'python3'
    assert call['args'][1]['path_list'] == ['1', '2']

def testRunConfTestsCheckSysLibs():

    buildtype = 'buildtype'
    cfgCtx = MockCfgCtx()
    tasks = AutoDict()
    tasks.task['sys-libs'] = 'lib1 lib2'
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-sys-libs', mandatory = False),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)
    call = cfgCtx.calls[0]
    assert call['func'] == 'check'
    assert call['args']['lib'] == 'lib1'
    assert call['args']['mandatory'] == False
    call = cfgCtx.calls[1]
    assert call['func'] == 'check'
    assert call['args']['lib'] == 'lib2'
    assert call['args']['mandatory'] == False

def testRunConfTestsCheckHeaders():

    buildtype = 'buildtype'
    cfgCtx = MockCfgCtx()
    tasks = AutoDict()
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-headers', names = 'header1 header2', mandatory = False),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)
    call = cfgCtx.calls[0]
    assert call['func'] == 'check'
    assert call['args']['header_name'] == 'header1'
    assert call['args']['mandatory'] == False
    call = cfgCtx.calls[1]
    assert call['func'] == 'check'
    assert call['args']['header_name'] == 'header2'
    assert call['args']['mandatory'] == False

def testRunConfTestsCheckLibs():

    buildtype = 'buildtype'
    cfgCtx = MockCfgCtx()
    tasks = AutoDict()
    tasks.task['$task.variant'] = buildtype
    tasks.task.conftests = [
        dict(act = 'check-libs', names = 'lib1 lib2', mandatory = False),
        dict(act = 'check-libs', names = 'lib3', autodefine = True),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)
    call = cfgCtx.calls[0]
    assert call['func'] == 'check'
    assert call['args']['lib'] == 'lib1'
    assert call['args']['mandatory'] == False
    assert 'define_name' not in call['args']
    call = cfgCtx.calls[1]
    assert call['func'] == 'check'
    assert call['args']['lib'] == 'lib2'
    assert call['args']['mandatory'] == False
    assert 'define_name' not in call['args']
    call = cfgCtx.calls[2]
    assert call['func'] == 'check'
    assert call['args']['lib'] == 'lib3'
    assert call['args']['define_name'] == 'HAVE_LIB_LIB3'

def testRunConfTestsWriteHeader():

    buildtype = 'buildtype'
    cfgCtx = MockCfgCtx()
    tasks = AutoDict()
    tasks['some task']['$task.variant'] = buildtype
    tasks['some task'].conftests = [
        dict(act = 'write-config-header',),
        dict(act = 'write-config-header', file = 'file1'),
        dict(act = 'write-config-header', file = 'file2', guard = 'myguard'),
    ]

    assist.runConfTests(cfgCtx, buildtype, tasks)
    call = cfgCtx.calls[0]
    assert call['func'] == 'write_config_header'
    assert call['args'][0] == joinpath(buildtype, 'some_task_config.h')
    assert call['args'][1]['guard'] == '_buildtype_some_task_config_h'.upper()
    call = cfgCtx.calls[1]
    assert call['func'] == 'write_config_header'
    assert call['args'][0] == joinpath(buildtype, 'file1')
    assert call['args'][1]['guard'] == '_buildtype_file1'.upper()
    call = cfgCtx.calls[2]
    assert call['func'] == 'write_config_header'
    assert call['args'][0] == joinpath(buildtype, 'file2')
    assert call['args'][1]['guard'] == 'myguard'

    cfgCtx = MockCfgCtx()
    cfgCtx.setenv(buildtype)
    cfgCtx.env['PROJECT_NAME'] = 'test prj'

    assist.runConfTests(cfgCtx, buildtype, tasks)
    call = cfgCtx.calls[0]
    assert call['func'] == 'write_config_header'
    assert call['args'][0] == joinpath(buildtype, 'some_task_config.h')
    assert call['args'][1]['guard'] == 'test_prj_buildtype_some_task_config_h'.upper()
    call = cfgCtx.calls[1]
    assert call['func'] == 'write_config_header'
    assert call['args'][0] == joinpath(buildtype, 'file1')
    assert call['args'][1]['guard'] == 'test_prj_buildtype_file1'.upper()
    call = cfgCtx.calls[2]
    assert call['func'] == 'write_config_header'
    assert call['args'][0] == joinpath(buildtype, 'file2')
    assert call['args'][1]['guard'] == 'myguard'

def testRunConfTestsUnknown():

    buildtype = 'buildtype'
    cfgCtx = MockCfgCtx()
    tasks = AutoDict()
    tasks.task.conftests = [
        dict(act = 'random act',),
    ]

    with pytest.raises(WafError):
        assist.runConfTests(cfgCtx, buildtype, tasks)
