# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import shutil
import pytest
from waflib.ConfigSet import ConfigSet
import tests.common as cmn
from zm import assist, toolchains, utils
from zm.autodict import AutoDict
from zm.constants import *

joinpath = os.path.join

class TestAssistFuncs(object):

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

    def testDeepCopyEnv(self):
        env = ConfigSet()
        env.test1 = 'test1'
        childenv = env.derive()
        childenv.test2 = 'test2'
        newenv = assist.deepcopyEnv(childenv)
        assert childenv.test1 == 'test1'
        assert childenv.test2 == 'test2'
        assert newenv.test1 == 'test1'
        assert newenv.test2 == 'test2'
        env.test1 = 'abc'
        assert childenv.test1 == 'abc'
        assert childenv.test2 == 'test2'
        assert newenv.test1 == 'test1'
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

        with cmn.capturedOutput(): # just supress any output
            assist.distclean(fakeConfPaths)

        assert not os.path.exists(fakeConfPaths.buildroot)
        assert os.path.exists(fakeConfPaths.projectroot)
        assert not os.path.exists(str(lockfile))
        if PLATFORM != 'windows':
            assert not os.path.exists(fakeConfPaths.buildsymlink)

class TestBuildConfHandler(object):

    def testInit(self):
        pass