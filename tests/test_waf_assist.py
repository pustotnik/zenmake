# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = too-many-statements

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from copy import deepcopy
from waflib.ConfigSet import ConfigSet
from waflib import Context
from zm import utils, db
from zm.waf import assist
from zm.autodict import AutoDict
from zm.constants import *
from zm.pathutils import PathsParam
from zm.features import ToolchainVars
import tests.common as cmn

joinpath = os.path.join
abspath = os.path.abspath
normpath = os.path.normpath
relpath = os.path.relpath
isfile = os.path.isfile

def testWriteZenMakeMetaFile(tmpdir):
    buildconffile = tmpdir.join("buildconf.py")
    buildconffile.write("buildconf")
    dir1 = tmpdir.mkdir("dir1")
    buildconffile2 = dir1.join("buildconf.yml")
    buildconffile2.write("buildconf")
    zmmetafile = tmpdir.join("zmmetafile")

    fakeConfPaths = AutoDict()
    fakeConfPaths.buildconffile = str(buildconffile)
    fakeConfPaths.zmmetafile = str(zmmetafile)

    fakeConfManager = AutoDict()
    fakeConfManager.root.confPaths = fakeConfPaths
    fakeConfManager.configs = [
        AutoDict(path = str(buildconffile)),
        AutoDict(path = str(buildconffile2)),
    ]

    monitFiles = [x.path for x in fakeConfManager.configs]

    assert not isfile(fakeConfPaths.zmmetafile)
    attrs = {'var': 1, 'd': 'zxc'}
    assist.writeZenMakeMetaFile(fakeConfPaths.zmmetafile, monitFiles, attrs)
    assert isfile(fakeConfPaths.zmmetafile)

    dbfile = db.PyDBFile(fakeConfPaths.zmmetafile, extension = '')
    cfgenv = dbfile.load(asConfigSet = True)
    assert 'rundir' in cfgenv
    assert 'topdir' in cfgenv
    assert 'outdir' in cfgenv
    assert 'monitfiles' in cfgenv
    assert cfgenv.monitfiles == [ str(buildconffile), str(buildconffile2) ]
    assert 'monithash' in cfgenv
    assert 'attrs' in cfgenv
    assert cfgenv.attrs == attrs

    _hash = utils.hashFiles(cfgenv.monitfiles)
    assert cfgenv.monithash == _hash

    assert 'toolenvs' in cfgenv
    tvars = ToolchainVars
    envVarNames = tvars.allSysFlagVars() + tvars.allSysVarsToSetToolchain()
    for name in envVarNames:
        assert name in cfgenv.toolenvs

def testMakeTasksCachePath():
    buildtype, zmcachedir = ('somename', 'somedir')
    path = assist.makeTasksCachePath(zmcachedir, buildtype)
    assert path == joinpath(zmcachedir, "%s.tasks" % buildtype)

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

def testSetTaskEnvVars():
    cfgEnvVars = ToolchainVars.allCfgFlagVars()

    toolchainSettings = AutoDict()
    toolchainSettings.gcc.vars = {}

    taskParamsFixture = []
    baseTaskParams = {
        'features' : ['cshlib'],
        'toolchain': ['gcc'],
    }
    for var in cfgEnvVars:
        taskParamsFixture.extend([
            dict(baseTaskParams, **{ var.lower() : 'var1' }),
            dict(baseTaskParams, **{ var.lower() : 'var1 var2' }),
            dict(baseTaskParams, **{ var.lower() : ['var1', 'var2'] }),
        ])

    for taskParams in taskParamsFixture:
        env = ConfigSet()
        assist.setTaskEnvVars(env, taskParams, toolchainSettings)
        for key, val in taskParams.items():
            if key in ('toolchain', 'features'):
                continue
            envkey = key.upper()
            assert envkey in env
            assert env[envkey] == utils.toList(val)

def testDetectTaskFeatures():
    taskParams = {}
    ctx = Context.Context(run_dir = os.getcwd())
    assert assist.detectTaskFeatures(ctx, taskParams) == []

    taskParams = { 'features' : '' }
    assert assist.detectTaskFeatures(ctx, taskParams) == []

    for ftype in ('stlib', 'shlib', 'program'):
        for lang in ('c', 'cxx'):
            fulltype = '%s%s' % (lang, ftype)

            taskParams = { 'features' : fulltype }
            assert sorted(assist.detectTaskFeatures(ctx, taskParams)) == sorted([
                lang, fulltype
            ])

            taskParams = { 'features' : [lang, fulltype] }
            assert sorted(assist.detectTaskFeatures(ctx, taskParams)) == sorted([
                lang, fulltype
            ])

def testHandleTaskIncludesParam():

    rootdir = abspath(joinpath(os.getcwd(), 'testroot')) # just any abs path
    startdir = abspath(joinpath(rootdir, 'subdir'))
    taskParams = {}
    _taskParams = deepcopy(taskParams)
    assist.handleTaskIncludesParam(_taskParams, startdir)
    assert _taskParams['includes'] == ['.']

    startDirs = [
        abspath(joinpath(rootdir, '.')),
        abspath(joinpath(rootdir, '..')),
        abspath(joinpath(rootdir, 'subdir')),
    ]
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

    def calcExpectedPaths(newStartdir, paramStartDir, paths):
        paths = utils.toList(paths)
        paths = [ joinpath(paramStartDir, x) for x in paths ]
        paths = [ normpath(relpath(x, newStartdir)) for x in paths ]
        return paths

    _paths = [(x, y) for x in pathsIncludes for y in pathsExportIncludes]
    for paramStartDir in startDirs:
        for incPaths, expPaths in _paths:
            taskParams = {
                'includes': PathsParam(incPaths, paramStartDir, kind = 'paths'),
            }

            if isinstance(expPaths, bool):
                taskParams['export-includes'] = expPaths
            else:
                taskParams['export-includes'] = \
                    PathsParam(expPaths, paramStartDir, kind = 'paths')

            _taskParams = deepcopy(taskParams)
            assist.handleTaskIncludesParam(_taskParams, startdir)

            includePaths = calcExpectedPaths(startdir, paramStartDir, incPaths)
            expected = ['.']
            expected.extend(includePaths)
            assert _taskParams['includes'] == expected

            if isinstance(expPaths, bool):
                if expPaths:
                    assert _taskParams['export-includes'] == expected
                else:
                    assert 'export-includes' not in _taskParams
            else:
                exportPaths = calcExpectedPaths(startdir, paramStartDir,
                                                expPaths)
                assert _taskParams['export-includes'] == exportPaths

def testHandleTaskSourceParam(tmpdir, mocker):

    """
    ./src/..
    ./zm/buildconf.py

    cwd = ./zm
    bconf.rootdir = .
    bconf.path = ./zm
    """

    rootdir = tmpdir
    cwd = tmpdir.mkdir("zm")
    srcroot = tmpdir.mkdir("src")
    srcroot.join('some', '2', "trash.txt").write("content", ensure = True)
    srcroot.join('some', '2', "main.c").write("content", ensure = True)
    srcroot.join('some', '2', "test.c").write("content", ensure = True)
    srcroot.join('some', '2', "test.h").write("content", ensure = True)
    srcroot.join('some', '2', "main.cpp").write("content", ensure = True)
    srcroot.join('some', '2', "test.cpp").write("content", ensure = True)
    srcroot.join('some', '1', "Test.cpp").write("content", ensure = True)


    ctx = Context.Context(run_dir = str(cwd)) # ctx.path = Node(run_dir)

    bconf = AutoDict(
        rootdir = str(rootdir),
        path = str(cwd),
        confPaths = AutoDict(buildroot = "build"),
    )
    def getbconf(pathNode):
        return bconf
    ctx.getbconf = mocker.MagicMock(side_effect = getbconf)

    def getStartDirNode(path):
        return None
    ctx.getStartDirNode = mocker.MagicMock(side_effect = getStartDirNode)

    taskParams = { '$startdir' : '.' }

    # empty
    taskParams['source'] = {}
    src = assist.handleTaskSourceParam(ctx, taskParams)
    assert src == []

    # find with wildcard

    srcParams = dict( startdir = 'src', )
    taskParams['source'] = srcParams
    realStartDir = abspath(joinpath(bconf.rootdir, srcParams['startdir']))

    # case 1
    srcParams['include'] = ['some/**/*.cpp']
    for _ in range(2): # to check with cache
        rv = assist.handleTaskSourceParam(ctx, taskParams)
        assert sorted([x.abspath() for x in rv]) == sorted([
            joinpath(realStartDir, 'some', '2', 'main.cpp'),
            joinpath(realStartDir, 'some', '2', 'test.cpp'),
            joinpath(realStartDir, 'some', '1', 'Test.cpp'),
        ])

    # case 2
    srcParams['include'] = ['**/*.cpp']
    srcParams['exclude'] = ['**/*test*']
    for _ in range(2): # to check with cache
        rv = assist.handleTaskSourceParam(ctx, taskParams)
        assert sorted([x.abspath() for x in rv]) == sorted([
            joinpath(realStartDir, 'some', '2', 'main.cpp'),
            joinpath(realStartDir, 'some', '1', 'Test.cpp'),
        ])

    # case 3
    srcParams['include'] = ['**/*.cpp', '**/*.c']
    srcParams['exclude'] = ['**/*test*']
    srcParams['ignorecase'] = True
    for _ in range(2): # to check with cache
        rv = assist.handleTaskSourceParam(ctx, taskParams)
        assert sorted([x.abspath() for x in rv]) == sorted([
            joinpath(realStartDir, 'some', '2', 'main.c'),
            joinpath(realStartDir, 'some', '2', 'main.cpp'),
        ])

    # find as is

    # case 4
    srcParams['paths'] = ['some/2/main.c']
    for _ in range(2): # to check with cache
        rv = assist.handleTaskSourceParam(ctx, taskParams)
        assert sorted([x.abspath() for x in rv]) == sorted([
            joinpath(realStartDir, 'some', '2', 'main.c'),
        ])

    # case 5
    srcParams['paths'] = ['some/2/main.c', 'some/2/test.c']
    for _ in range(2): # to check with cache
        rv = assist.handleTaskSourceParam(ctx, taskParams)
        assert sorted([x.abspath() for x in rv]) == sorted([
            joinpath(realStartDir, 'some', '2', 'main.c'),
            joinpath(realStartDir, 'some', '2', 'test.c'),
        ])

    # case 6
    srcParams['paths'] = ['some/2/main.c', 'some/1/Test.cpp']
    for _ in range(2): # to check with cache
        rv = assist.handleTaskSourceParam(ctx, taskParams)
        assert sorted([x.abspath() for x in rv]) == sorted([
            joinpath(realStartDir, 'some', '2', 'main.c'),
            joinpath(realStartDir, 'some', '1', 'Test.cpp'),
        ])

def testDistclean(tmpdir, monkeypatch):

    buildroot = tmpdir.mkdir("build")
    buildroot.join("trash.txt").write("content")
    startdir = tmpdir.mkdir("project")
    startdir.join("trash2.txt").write("content2")

    fakeConfPaths = AutoDict()
    fakeConfPaths.buildroot = str(buildroot.realpath())
    fakeConfPaths.realbuildroot = fakeConfPaths.buildroot
    fakeConfPaths.startdir = str(startdir.realpath())
    fakeConfPaths.rootdir = fakeConfPaths.startdir

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
