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
import tests.common as cmn
from zm import assist, toolchains, utils
from zm.autodict import AutoDict
from zm.constants import *

joinpath = os.path.join

class TestAssist(object):

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
        bconfPaths = AutoDict()
        bconfPaths.buildout = joinpath('some', 'path')
        dirName = 'somedir'
        targetName = 'sometarget'
        path = assist.makeTargetPath(bconfPaths, dirName, targetName)
        assert path == joinpath(bconfPaths.buildout, dirName, targetName)

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

    def testDetectAllTaskFeatures(self):
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
