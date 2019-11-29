# coding=utf-8
#

# _pylint: skip-file
# pylint: disable = wildcard-import, unused-wildcard-import, unused-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from copy import deepcopy
import pytest
from waflib.ConfigSet import ConfigSet
from waflib import Context
from waflib.Errors import WafError
import tests.common as cmn
from zm import toolchains, utils
from zm.waf import assist
from zm.autodict import AutoDict
from zm.constants import *

joinpath = os.path.join
abspath = os.path.abspath
normpath = os.path.normpath
relpath = os.path.relpath

def testDumpZenMakeCommonFile(tmpdir):
    buildconffile = tmpdir.join("buildconf.py")
    buildconffile.write("buildconf")
    dir1 = tmpdir.mkdir("dir1")
    buildconffile2 = dir1.join("buildconf.yml")
    buildconffile2.write("buildconf")
    zmcmnconfset = tmpdir.join("zmcmnconfset")

    fakeConfPaths = AutoDict()
    fakeConfPaths.buildconffile = str(buildconffile)
    fakeConfPaths.zmcmnconfset = str(zmcmnconfset)

    fakeConfManager = AutoDict()
    fakeConfManager.root.confPaths = fakeConfPaths
    fakeConfManager.configs = [
        AutoDict(path = str(buildconffile)),
        AutoDict(path = str(buildconffile2)),
    ]

    assert not os.path.exists(fakeConfPaths.zmcmnconfset)
    assist.dumpZenMakeCmnConfSet(fakeConfManager)
    assert os.path.isfile(fakeConfPaths.zmcmnconfset)

    cfgenv = ConfigSet(fakeConfPaths.zmcmnconfset)
    assert 'monitfiles' in cfgenv
    assert cfgenv.monitfiles == [ str(buildconffile), str(buildconffile2) ]
    assert 'monithash' in cfgenv

    _hash = 0
    for file in cfgenv.monitfiles:
        _hash = utils.mkHashOfStrings((_hash, utils.readFile(file, 'rb')))
    assert cfgenv.monithash == _hash

    assert 'toolenvs' in cfgenv
    cinfo = toolchains.CompilersInfo
    envVarNames = cinfo.allFlagVars() + cinfo.allVarsToSetCompiler()
    for name in envVarNames:
        assert name in cfgenv.toolenvs

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
        assist.setTaskToolchainEnvVars(env, taskParams)
        for key, val in taskParams.items():
            envkey = key.upper()
            assert envkey in env
            assert env[envkey] == utils.toList(val)

def testDetectConfTaskFeatures():
    taskParams = {}
    assert assist.detectConfTaskFeatures(taskParams) == []

    taskParams = { 'features' : '' }
    assert assist.detectConfTaskFeatures(taskParams) == []

    for ftype in ('stlib', 'shlib', 'program'):
        for lang in ('c', 'cxx'):
            fulltype = '%s%s' % (lang, ftype)

            taskParams = { 'features' : fulltype }
            assert sorted(assist.detectConfTaskFeatures(taskParams)) == sorted([
                lang, fulltype
            ])

            taskParams = { 'features' : [lang, fulltype] }
            assert sorted(assist.detectConfTaskFeatures(taskParams)) == sorted([
                lang, fulltype
            ])

def testHandleTaskIncludesParam():

    rootdir = abspath(joinpath(os.getcwd(), 'testroot')) # just any abs path
    startdir = abspath(joinpath(rootdir, 'subdir'))
    taskParams = {}
    _taskParams = deepcopy(taskParams)
    assist.handleTaskIncludesParam(_taskParams, rootdir, startdir)
    assert _taskParams['includes'] == ['.']

    startDirs = [
        abspath(joinpath(rootdir, '.')),
        abspath(joinpath(rootdir, '..')),
        abspath(joinpath(rootdir, 'subdir')),
    ]
    paramStartDirs = [ '.', 'sub1', '..', ]
    pathsIncludes = [
        'inc1 inc2',
        [
            joinpath(os.getcwd(), '123', 'inc3'),
            joinpath(os.getcwd(), '456', 'inc4'),
        ],
    ]
    pathsExportIncludes = [
        False,
        True,
        'inc1 inc2',
        [
            joinpath(os.getcwd(), '123', 'inc3'),
            joinpath(os.getcwd(), '456', 'inc4'),
        ],
    ]

    def calcExpectedPaths(rootdir, startdir, paramStartDir, paths):
        expectedStartDir = joinpath(rootdir, paramStartDir)
        paths = utils.toList(paths)
        paths = [ joinpath(expectedStartDir, x) for x in paths ]
        paths = [ normpath(relpath(x, startdir)) for x in paths ]
        return paths

    _startDirs = [(x, y) for x in startDirs for y in paramStartDirs]
    _paths = [(x, y) for x in pathsIncludes for y in pathsExportIncludes]
    for startdir, paramStartDir in _startDirs:
        for incPaths, expPaths in _paths:
            taskParams = {
                'includes': { 'paths': incPaths, 'startdir' : paramStartDir, },
                'export-includes' : { 'paths': expPaths, 'startdir' : paramStartDir, },
            }

            _taskParams = deepcopy(taskParams)
            assist.handleTaskIncludesParam(_taskParams, rootdir, startdir)

            includePaths = calcExpectedPaths(rootdir, startdir, paramStartDir,
                                            taskParams['includes']['paths'])
            expected = ['.']
            expected.extend(includePaths)
            assert _taskParams['includes'] == expected

            if isinstance(expPaths, bool):
                if expPaths:
                    assert _taskParams['export-includes'] == expected
                else:
                    assert 'export-includes' not in _taskParams
            else:
                exportPaths = calcExpectedPaths(rootdir, startdir, paramStartDir,
                                        taskParams['export-includes']['paths'])
                assert _taskParams['export-includes'] == exportPaths

def testHandleTaskSourceParam(mocker):

    cwd = os.getcwd()
    ctx = Context.Context(run_dir = cwd) # ctx.path = Node(run_dir)

    bconf = AutoDict(rootdir = abspath(joinpath(cwd, '..')), path = cwd)
    def getbconf():
        return bconf
    ctx.getbconf = mocker.MagicMock(side_effect = getbconf)

    nodes = []
    def finddir(path):
        node = ctx.path.make_node(path)
        node.ant_glob = mocker.MagicMock(return_value = 'wildcard')
        node.find_node = mocker.MagicMock(return_value = 'file')
        nodes.append(node)
        return node
    ctx.path.find_dir = mocker.MagicMock(side_effect = finddir)

    taskParams = {}
    src = assist.handleTaskSourceParam(ctx, taskParams)
    assert src == []

    # find with wildcard

    taskParams = {
        'source' : dict( startdir = 'asdf', ),
    }
    srcParams = taskParams['source']
    realStartDir = abspath(joinpath(bconf.rootdir, srcParams['startdir']))

    # case 1
    del nodes[:]
    srcParams['include'] = 'some/**/*.cpp'
    rv = assist.handleTaskSourceParam(ctx, taskParams)
    assert rv == 'wildcard'
    assert len(nodes) == 1
    assert nodes[0].abspath() == realStartDir
    assert nodes[0].ant_glob.mock_calls == [
        mocker.call(incl = 'some/**/*.cpp', excl = '',
                ignorecase = False, remove = mocker.ANY)
    ]

    # case 2
    del nodes[:]
    srcParams['include'] = 's/**/*.cpp'
    srcParams['exclude'] = 'd/**/.cpp'
    rv = assist.handleTaskSourceParam(ctx, taskParams)
    assert rv == 'wildcard'
    assert len(nodes) == 1
    assert nodes[0].abspath() == realStartDir
    assert nodes[0].ant_glob.mock_calls == [
        mocker.call(incl = 's/**/*.cpp', excl = 'd/**/.cpp',
                ignorecase = False, remove = mocker.ANY),
    ]

    # case 3
    del nodes[:]
    srcParams.pop('exclude', None)
    srcParams['include'] = 's/**/*.cpp'
    srcParams['ignorecase'] = True
    rv = assist.handleTaskSourceParam(ctx, taskParams)
    assert rv == 'wildcard'
    assert len(nodes) == 1
    assert nodes[0].abspath() == realStartDir
    assert nodes[0].ant_glob.mock_calls == [
        mocker.call(incl = 's/**/*.cpp', excl = '',
                ignorecase = True, remove = mocker.ANY),
    ]

    # find as is
    taskParams = {
        'source' : dict( startdir = joinpath(cwd, '123'), ),
    }
    srcParams = taskParams['source']
    realStartDir = abspath(joinpath(bconf.rootdir, srcParams['startdir']))

    # case 4
    del nodes[:]
    srcParams['paths'] = 'a.c'
    rv = assist.handleTaskSourceParam(ctx, taskParams)
    assert rv == ['file']
    assert len(nodes) == 1
    assert nodes[0].abspath() == realStartDir
    assert nodes[0].find_node.mock_calls == [
        mocker.call('a.c'),
    ]

    # case 5
    del nodes[:]
    srcParams['paths'] = 'a.c b.c'
    rv = assist.handleTaskSourceParam(ctx, taskParams)
    assert rv == ['file', 'file']
    assert len(nodes) == 1
    assert nodes[0].abspath() == realStartDir
    assert nodes[0].find_node.mock_calls == [
        mocker.call('a.c'),
        mocker.call('b.c'),
    ]

def testDistclean(tmpdir, monkeypatch):

    buildroot = tmpdir.mkdir("build")
    trashfile = buildroot.join("trash.txt")
    trashfile.write("content")
    startdir = tmpdir.mkdir("project")
    trashfile = startdir.join("trash2.txt")
    trashfile.write("content2")

    fakeConfPaths = AutoDict()
    fakeConfPaths.buildroot = str(buildroot.realpath())
    fakeConfPaths.realbuildroot = fakeConfPaths.buildroot
    fakeConfPaths.startdir = str(startdir.realpath())

    assert os.path.isdir(fakeConfPaths.buildroot)
    assert os.path.isdir(fakeConfPaths.startdir)

    if PLATFORM != 'windows':
        buildsymlink = tmpdir.join("buildlink")
        buildsymlink.mksymlinkto(buildroot)
        fakeConfPaths.buildroot = str(buildsymlink)
        assert os.path.islink(fakeConfPaths.buildroot)

    lockfileName = 'testlockfile'
    lockfile = startdir.join(lockfileName)
    lockfile.write("test lock")
    assert os.path.isfile(str(lockfile))

    from waflib import Options
    monkeypatch.setattr(Options, 'lockfile', lockfileName)

    with cmn.capturedOutput(): # just supress any output
        assist.distclean(fakeConfPaths)

    assert not os.path.exists(fakeConfPaths.realbuildroot)
    assert not os.path.exists(fakeConfPaths.buildroot)
    assert os.path.exists(fakeConfPaths.startdir)
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
