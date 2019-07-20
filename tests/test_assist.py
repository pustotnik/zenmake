# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import shutil
from copy import deepcopy
import pytest
from waflib.ConfigSet import ConfigSet
import tests.common as cmn
from zm import assist, toolchains, buildconfutil, utils
from zm.autodict import AutoDict
from zm.error import *
from zm.constants import *

joinpath = os.path.join

@pytest.fixture
def testingBuildConf():
    buildconf = AutoDict()
    buildconf.__file__ = os.path.abspath('buildconf.py')
    buildconf.__name__ = 'buildconf'
    buildconf.buildroot    = 'buildroot'
    buildconf.buildsymlink = 'buildsymlink'
    buildconf.project.root = 'prjroot'
    buildconf.project.name = 'test-project'
    buildconf.project.version = '1.2.3.4'
    buildconf.srcroot = 'src'

    return buildconf

class TestAssistFuncs(object):

    def testDumpZenMakeCommonFile(self, tmpdir):
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

    def testLoadTasksFromCache(self, tmpdir):
        cachefile = tmpdir.join("cachefile")
        assert assist.loadTasksFromCache(str(cachefile)) == {}
        cachedata = ConfigSet()
        cachedata.something = 11
        cachedata.store(str(cachefile))
        assert assist.loadTasksFromCache(str(cachefile)) == {}
        cachedata.alltasks = dict( a = 1, b =2 )
        cachedata.store(str(cachefile))
        assert assist.loadTasksFromCache(str(cachefile)) == cachedata.alltasks

    def testMakeTargetPath(self):
        fakeCtx = AutoDict()
        fakeCtx.out_dir = joinpath('some', 'path')
        dirName = 'somedir'
        targetName = 'sometarget'
        path = assist.makeTargetPath(fakeCtx, dirName, targetName)
        assert path == joinpath(fakeCtx.out_dir, dirName, targetName)

    def testMakeCacheConfFileName(self):
        name, zmcachedir = ('somename', 'somedir')
        path = assist.makeCacheConfFileName(zmcachedir, name)
        assert path == joinpath(zmcachedir, name + ZENMAKE_CACHE_NAMESUFFIX)

    def testGetTaskVariantName(self):
        buildtype, taskName = ('ddd', 'bbb')
        name = assist.getTaskVariantName(buildtype, taskName)
        assert name == '%s.%s' % (buildtype, taskName)

    def testCopyEnv(self):
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

    def testDeepCopyEnv(self):
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

    def testSetTaskEnvVars(self):
        cfgEnvVars = toolchains.CompilersInfo.allCfgEnvVars()

        taskParamsFixture = []
        for var in cfgEnvVars:
            taskParamsFixture.extend([
                { var.lower() : 'var1' },
                { var.lower() : 'var1 var2' },
                { var.lower() : ['var1', 'var2'] },
            ])

        for taskParams in taskParamsFixture:
            env = dict()
            assist.setTaskEnvVars(env, taskParams)
            for key, val in taskParams.items():
                envkey = key.upper()
                assert envkey in env
                assert env[envkey] == utils.toList(val)

    def testHandleTaskIncludesParam(self):
        taskParams = {}
        srcroot = joinpath(os.getcwd(), 'testsrcroot') # just any abs path
        includes = assist.handleTaskIncludesParam(taskParams, srcroot)
        assert includes == ['.']

        taskParams = { 'includes': 'inc1 inc2' }
        includes = assist.handleTaskIncludesParam(taskParams, srcroot)
        assert includes == [
            joinpath(srcroot, taskParams['includes'].split()[0]),
            joinpath(srcroot, taskParams['includes'].split()[1]),
            '.'
        ]

        taskParams = { 'includes': ['inc1', 'inc2'] }
        includes = assist.handleTaskIncludesParam(taskParams, srcroot)
        assert includes == [
            joinpath(srcroot, taskParams['includes'][0]),
            joinpath(srcroot, taskParams['includes'][1]),
            '.'
        ]

        abspaths = [
            joinpath(os.getcwd(), '123', 'inc3'),
            joinpath(os.getcwd(), '456', 'inc4')]
        taskParams = { 'includes': abspaths }
        includes = assist.handleTaskIncludesParam(taskParams, srcroot)
        assert includes == [ abspaths[0], abspaths[1], '.' ]

    def testDistclean(self, tmpdir, monkeypatch):

        buildroot = tmpdir.mkdir("build")
        trashfile = buildroot.join("trash.txt")
        trashfile.write("content")
        projectroot = tmpdir.mkdir("project")
        trashfile = projectroot.join("trash2.txt")
        trashfile.write("content2")

        fakeConfPaths = AutoDict()
        fakeConfPaths.buildroot = str(buildroot.realpath())
        fakeConfPaths.projectroot = str(projectroot.realpath())

        assert os.path.isdir(fakeConfPaths.buildroot)
        assert os.path.isdir(fakeConfPaths.projectroot)

        if PLATFORM != 'windows':
            buildsymlink = tmpdir.join("buildlink")
            buildsymlink.mksymlinkto(buildroot)
            fakeConfPaths.buildsymlink = str(buildsymlink)
            assert os.path.exists(fakeConfPaths.buildsymlink)
            assert os.path.islink(fakeConfPaths.buildsymlink)
        else:
            fakeConfPaths.buildsymlink = None

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

        assert not os.path.exists(fakeConfPaths.buildroot)
        assert os.path.exists(fakeConfPaths.projectroot)
        assert not os.path.exists(str(wscriptfile))
        assert not os.path.exists(str(lockfile))
        if PLATFORM != 'windows':
            assert not os.path.exists(fakeConfPaths.buildsymlink)

        # rare cases
        buildsymlink = tmpdir.mkdir("buildsymlink")
        fakeConfPaths.buildsymlink = str(buildsymlink)
        assert os.path.isdir(fakeConfPaths.buildsymlink)

        if PLATFORM != 'windows':
            somedir = tmpdir.mkdir("somedir")
            buildroot = tmpdir.join("buildroot")
            buildroot.mksymlinkto(somedir)
            fakeConfPaths.buildroot = str(buildroot)
            assert os.path.islink(fakeConfPaths.buildroot)

        with cmn.capturedOutput(): # just supress any output
            assist.distclean(fakeConfPaths)
        assert not os.path.exists(fakeConfPaths.buildsymlink)
        assert not os.path.exists(fakeConfPaths.buildroot)

    def testIsBuildConfFake(self):
        fakeBuildConf = utils.loadPyModule('zm.fakebuildconf', withImport = False)
        assert assist.isBuildConfFake(fakeBuildConf)

        # find first real buildconf.py and check
        prjdir = None
        for dirpath, _, filenames in os.walk(cmn.TEST_PROJECTS_DIR):
            if 'buildconf.py' in filenames:
                prjdir = dirpath
                break
        realBuildConf = utils.loadPyModule('buildconf', prjdir, withImport = False)
        assert not assist.isBuildConfFake(realBuildConf)

class TestBuildConfPaths(object):

    def testAll(self, testingBuildConf):
        fakeBuildConf = testingBuildConf
        bcpaths = assist.BuildConfPaths(fakeBuildConf)

        dirname    = os.path.dirname
        abspath    = os.path.abspath

        assert bcpaths.buildconffile == abspath(fakeBuildConf.__file__)
        assert bcpaths.buildconfdir  == dirname(bcpaths.buildconffile)
        assert bcpaths.buildroot     == joinpath(bcpaths.buildconfdir,
                                                   fakeBuildConf.buildroot)
        assert bcpaths.buildsymlink  == joinpath(bcpaths.buildconfdir,
                                                   fakeBuildConf.buildsymlink)
        assert bcpaths.buildout      == joinpath(bcpaths.buildroot, BUILDOUTNAME)
        assert bcpaths.projectroot   == joinpath(bcpaths.buildconfdir,
                                                   fakeBuildConf.project['root'])
        assert bcpaths.srcroot       == joinpath(bcpaths.buildconfdir,
                                                   fakeBuildConf.srcroot)
        assert bcpaths.wscriptout    == bcpaths.buildout
        assert bcpaths.wscriptfile   == joinpath(bcpaths.wscripttop, WSCRIPT_NAME)
        assert bcpaths.wscriptdir    == dirname(bcpaths.wscriptfile)
        assert bcpaths.wafcachedir   == joinpath(bcpaths.buildout,
                                                 WAF_CACHE_DIRNAME)
        assert bcpaths.wafcachefile  == joinpath(bcpaths.wafcachedir,
                                                 WAF_CACHE_NAMESUFFIX)
        assert bcpaths.zmcachedir    == bcpaths.wafcachedir
        assert bcpaths.zmcmnfile     == joinpath(bcpaths.buildout,
                                                 ZENMAKE_COMMON_FILENAME)
        assert bcpaths.wscripttop == bcpaths.projectroot or \
               bcpaths.wscripttop == bcpaths.buildroot

@pytest.mark.usefixtures("unsetEnviron")
class TestBuildConfHandler(object):

    def testInit(self, testingBuildConf):
        buildconf = testingBuildConf
        confHandler = assist.BuildConfHandler(buildconf)
        assert not confHandler.cmdLineHandled
        assert confHandler.conf == buildconf
        assert confHandler.projectName == buildconf.project.name
        assert confHandler.projectVersion == buildconf.project.version
        assert confHandler.confPaths == assist.BuildConfPaths(buildconf)

    def testDefaultBuildType(self, testingBuildConf):
        buildconf = testingBuildConf

        confHandler = assist.BuildConfHandler(buildconf)
        assert confHandler.defaultBuildType == ''

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abc = {}
        buildconf.buildtypes.default = 'mybuildtype'
        confHandler = assist.BuildConfHandler(buildconf)
        assert confHandler.defaultBuildType == 'mybuildtype'

        buildconf.platforms = AutoDict({
            PLATFORM : AutoDict(valid = ['abc'], )
        })
        confHandler = assist.BuildConfHandler(buildconf)
        assert confHandler.defaultBuildType == 'mybuildtype'

        buildconf.platforms[PLATFORM].default = 'abc'
        confHandler = assist.BuildConfHandler(buildconf)
        assert confHandler.defaultBuildType == 'abc'

        buildconf.platforms[PLATFORM].default = 'void'
        confHandler = assist.BuildConfHandler(buildconf)
        with pytest.raises(ZenMakeError):
            bt = confHandler.defaultBuildType

    def testSelectedBuildType(self, testingBuildConf):
        buildconf = testingBuildConf
        clicmd = AutoDict()

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        confHandler = assist.BuildConfHandler(buildconf)
        with pytest.raises(ZenMakeLogicError):
            bt = confHandler.selectedBuildType

        clicmd.args.buildtype = 'mybuildtype'
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.selectedBuildType == clicmd.args.buildtype

    def testSupportedBuildTypes(self, testingBuildConf):
        buildconf = testingBuildConf

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}
        confHandler = assist.BuildConfHandler(buildconf)
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'abcbt'
        ])

        buildconf.tasks.test.buildtypes.extrabtype = {}
        confHandler = assist.BuildConfHandler(buildconf)
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'abcbt', 'extrabtype'
        ])

        buildconf.platforms[PLATFORM] = AutoDict()
        confHandler = assist.BuildConfHandler(buildconf)
        with pytest.raises(ZenMakeError):
            empty = confHandler.supportedBuildTypes

        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'invalid' ]
        confHandler = assist.BuildConfHandler(buildconf)
        with pytest.raises(ZenMakeError):
            empty = confHandler.supportedBuildTypes

        buildconf.platforms[PLATFORM].valid = [ 'mybuildtype', 'extrabtype' ]
        confHandler = assist.BuildConfHandler(buildconf)
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'extrabtype'
        ])

        buildconf.buildtypes.default = 'mybuildtype'
        confHandler = assist.BuildConfHandler(buildconf)
        assert sorted(confHandler.supportedBuildTypes) == sorted([
            'mybuildtype', 'extrabtype'
        ])


    def testHandleCmdLineArgs(self, testingBuildConf):

        clicmd = AutoDict()
        clicmd.args.buildtype = 'mybuildtype'

        fakeBuildConf = utils.loadPyModule('zm.fakebuildconf', withImport = False)
        buildconfutil.initDefaults(fakeBuildConf)
        confHandler = assist.BuildConfHandler(fakeBuildConf)
        with pytest.raises(ZenMakeError):
            confHandler.handleCmdLineArgs(clicmd)

        buildconf = testingBuildConf
        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.default = 'mybuildtype'

        confHandler = assist.BuildConfHandler(buildconf)
        assert not confHandler.cmdLineHandled

        with pytest.raises(ZenMakeError):
            confHandler.handleCmdLineArgs(AutoDict())

        confHandler.handleCmdLineArgs(clicmd)
        # Hm, all other results of this method is checked in testSupportedBuildTypes
        assert confHandler.cmdLineHandled

    def testTasks(self, testingBuildConf, monkeypatch):
        buildconf = testingBuildConf

        # CASE: invalid use
        confHandler = assist.BuildConfHandler(buildconf)
        with pytest.raises(ZenMakeLogicError):
            empty = confHandler.tasks

        buildconf.buildtypes.mybuildtype = {}
        buildconf.buildtypes.abcbt = {}
        clicmd = AutoDict()
        clicmd.args.buildtype = 'mybuildtype'

        # save base fixture
        buildconf = deepcopy(testingBuildConf)

        # CASE: just empty buildconf.tasks
        confHandler = assist.BuildConfHandler(buildconf)
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == {}
        # this assert just for in case
        assert confHandler.selectedBuildType == 'mybuildtype'

        # CASE: just some buildconf.tasks, nothing else
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '1'
        buildconf.tasks.test2.param2 = '2'
        confHandler = assist.BuildConfHandler(buildconf)
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == buildconf.tasks

        # CASE: some buildconf.tasks and buildconf.buildtypes
        # with non-empty selected buildtype
        # buildtype 'mybuildtype' should be selected at this moment
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '111'
        buildconf.tasks.test2.param2 = '222'
        buildconf.buildtypes.mybuildtype = { 'cxxflags' : '-O2' }

        expected = deepcopy(buildconf.tasks)
        for task in expected:
            expected[task].update(deepcopy(buildconf.buildtypes.mybuildtype))
        # self checking
        assert expected.test1.cxxflags == '-O2'
        assert expected.test2.cxxflags == '-O2'

        confHandler = assist.BuildConfHandler(buildconf)
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == expected

        # CASE: some buildconf.tasks and one task has own buildtypes
        # with non-empty selected buildtype
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = 'p1'
        buildconf.tasks.test2.param2 = 'p2'
        buildconf.tasks.test2.buildtypes.mybuildtype = { 'cxxflags' : '-Os' }

        expected = deepcopy(buildconf.tasks)
        del expected.test2['buildtypes']
        expected.test2.update(deepcopy(buildconf.tasks.test2.buildtypes.mybuildtype))
        # self checking
        assert expected.test2.cxxflags == '-Os'

        confHandler = assist.BuildConfHandler(buildconf)
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == expected

        # CASE: some buildconf.tasks, buildconf.buildtypes
        # with non-empty selected buildtype and one task has own buildtypes
        # with non-empty selected buildtype that overrides value from buildconf.buildtypes
        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = 'p1'
        buildconf.tasks.test2.param2 = 'p2'
        buildconf.buildtypes.mybuildtype = { 'cxxflags' : '-O2' }
        buildconf.tasks.test2.buildtypes.mybuildtype = { 'cxxflags' : '-O1' }

        expected = deepcopy(buildconf.tasks)
        for task in expected:
            expected[task].update(deepcopy(buildconf.buildtypes.mybuildtype))
        del expected.test2['buildtypes']
        expected.test2.update(deepcopy(buildconf.tasks.test2.buildtypes.mybuildtype))
        # self checking
        assert expected.test1.cxxflags == '-O2'
        assert expected.test2.cxxflags == '-O1'

        confHandler = assist.BuildConfHandler(buildconf)
        confHandler.handleCmdLineArgs(clicmd)
        assert confHandler.tasks == expected

        # CASE: influence of compiler flags from system environment
        cinfo = toolchains.CompilersInfo

        buildconf = deepcopy(testingBuildConf)
        buildconf.tasks.test1.param1 = '111'
        buildconf.tasks.test2.param2 = '222'

        testOldVal = 'val1 val2'
        testNewVal = 'val11 val22'
        testNewValAsList = utils.toList(testNewVal)
        flagVars = cinfo.allFlagVars()
        for var in flagVars:
            param = var.lower()
            buildconf.buildtypes.mybuildtype = { param : testOldVal }
            expected = deepcopy(buildconf.tasks)
            for task in expected:
                expected[task].update({ param : testNewValAsList })
            # self checking
            assert expected.test1[param] == testNewValAsList
            assert expected.test2[param] == testNewValAsList
            monkeypatch.setenv(var, testNewVal)

            confHandler = assist.BuildConfHandler(buildconf)
            confHandler.handleCmdLineArgs(clicmd)
            assert confHandler.tasks == expected

            monkeypatch.delenv(var, raising = False)

        # CASE: influence of compiler var from system environment
        cinfo = toolchains.CompilersInfo
        buildconf = deepcopy(testingBuildConf)
        testOldVal = 'old-compiler'
        testNewVal = 'new-compiler'
        toolchainVars = cinfo.allVarsToSetCompiler()
        for var in toolchainVars:
            param = var.lower()
            buildconf.tasks.test1.features = ''
            buildconf.tasks.test1.toolchain = testOldVal
            buildconf.tasks.test2.features = param
            buildconf.tasks.test2.toolchain = testOldVal
            expected = deepcopy(buildconf.tasks)
            expected.test1.toolchain = testOldVal
            expected.test2.toolchain = testNewVal

            monkeypatch.setenv(var, testNewVal)

            confHandler = assist.BuildConfHandler(buildconf)
            confHandler.handleCmdLineArgs(clicmd)
            assert confHandler.tasks == expected

            monkeypatch.delenv(var, raising = False)