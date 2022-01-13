# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = unused-argument, no-member, attribute-defined-outside-init
# pylint: disable = too-many-lines, too-many-branches, too-many-statements
# pylint: disable = line-too-long

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import re
import subprocess
import shutil
import platform as _platform
from collections import defaultdict
from copy import copy, deepcopy

#from waflib import Context
from waflib.ConfigSet import ConfigSet
from zm import starter
from zm import utils, zipapp, db
from zm.pyutils import stringtype
from zm.waf import assist
from zm.autodict import AutoDict
from zm.buildconf import loader as bconfloader
from zm.buildconf.processing import ConfManager as BuildConfManager
from zm.constants import ZENMAKE_BUILDMETA_FILENAME, PLATFORM, APPNAME
from zm.constants import BUILDOUTNAME, WAF_CONFIG_LOG, PYTHON_EXE
from zm.features import TASK_TARGET_FEATURES
from zm.buildconf.scheme import KNOWN_CONF_PARAM_NAMES

import tests.common as cmn

joinpath = os.path.join
isfile = os.path.isfile
isdir = os.path.isdir
islink = os.path.islink

ZM_BIN = cmn.ZENMAKE_DIR # it's a dir but it contains __main__.py
PYTHON_VER = _platform.python_version()

zmExes = {}
_cache = AutoDict()

def getZmExecutables():

    tmpdir = cmn.SHARED_TMP_DIR
    zipAppFile = joinpath(tmpdir, zipapp.ZIPAPP_NAME)
    if zmExes:
        return list(zmExes.keys())

    zmExes['normal'] = [PYTHON_EXE, ZM_BIN]

    cmd = zmExes['normal'] + ['zipapp', '--destdir', tmpdir]
    # pylint: disable = consider-using-with
    devnull = open(os.devnull, 'w')
    subprocess.call(cmd, stdout = devnull)
    assert isfile(zipAppFile)

    # On Windows 10 files *.pyz can be used as is because there is
    # a launcher (python.exe) that assosiated with this file extension in
    # the system. But python module subprocess cannot do it. So it needs to
    # specify python executable.
    # Also on all platforms to ensure that selected version of python is used
    # we should specify python executable. Otherwise default system python
    # will be used.
    zmExes['zipapp'] = [PYTHON_EXE, zipAppFile]
    return list(zmExes.keys())

def runZm(self, cmdline, env = None):

    zmExe = self.zmExe if hasattr(self, 'zmExe') else [PYTHON_EXE, ZM_BIN]
    cmdLine = zmExe + utils.toList(cmdline)

    _env = os.environ.copy()
    if env:
        _env.update(env)

    kwargs = {
        'cwd' : self.cwd,
        'env' : _env,
        'stdErrToOut' : True,
        'timeout' : 60 * 15,
    }

    self.zmresult = utils.runCmd(cmdLine, **kwargs)
    return self.zmresult.exitcode, self.zmresult.stdout, self.zmresult.stderr

def printOutputs(testSuit):
    zmInfo = getattr(testSuit, 'zmresult', None)
    if not zmInfo:
        return
    for param in ('stdout', 'stderr'):
        out = getattr(zmInfo, param, None)
        if out:
            print('\n' + out)

    def makeConfigLogPath(buildDirName):
        path = joinpath(testSuit.cwd, buildDirName)
        if BUILDOUTNAME:
            path = joinpath(path, BUILDOUTNAME)
        return joinpath(path, WAF_CONFIG_LOG)

    printConfigLog = os.environ.get('ZENMAKE_TESTING_PRINT_CONFIG_LOG', True)
    if printConfigLog:
        printConfigLog = utils.envValToBool(printConfigLog)

    if not printConfigLog:
        return

    configLog = makeConfigLogPath('build')
    if not isfile(configLog):
        configLog = makeConfigLogPath('_build')
    if isfile(configLog):
        print('\n== CONFIG LOG %s:\n' % configLog)
        with open(configLog) as file:
            print(file.read())

def printErrorOnFailed(testSuit, request):
    rep_call = getattr(request.node, 'rep_call', None)
    if not rep_call or rep_call.failed:
        printOutputs(testSuit)
        return True
    return False

def setupTest(self, request, tmpdir):

    #testName = request.node.originalname
    #if not testName:
    #    testName = request.node.name

    projectDirName = 'prj'

    # On windows with pytest it gets too long path
    useAltTmpTestDir = PLATFORM == 'windows'

    if useAltTmpTestDir:
        projectDirName = '_' # shortest name
        tmpdirForTests = cmn.SHARED_TMP_DIR
        tmptestDir = joinpath(tmpdirForTests, projectDirName)
        shutil.rmtree(tmptestDir, ignore_errors = True)
    else:
        tmptestDir = joinpath(str(tmpdir.realpath()), projectDirName)

    def copytreeIgnore(src, names):
        # don't copy build dir/files
        if ZENMAKE_BUILDMETA_FILENAME in names:
            return names
        return ['build', '_build']

    self.outputPrjDirName = projectDirName

    testPath = request if isinstance(request, stringtype) else request.param
    self.testDirPath = testPath
    testPathParts = testPath.split(os.sep)
    currentPrjDir = os.sep.join(testPathParts[:2])
    currentPrjDir = joinpath(cmn.TEST_PROJECTS_DIR, currentPrjDir)

    prjBuildDir = joinpath(currentPrjDir, 'build')
    if os.path.exists(prjBuildDir):
        prjBuildDir = os.path.realpath(prjBuildDir)
        if os.path.isdir(prjBuildDir):
            shutil.rmtree(prjBuildDir, ignore_errors = True)

    copySymlinksAsIs = PLATFORM != 'windows'
    shutil.copytree(currentPrjDir, tmptestDir, symlinks = copySymlinksAsIs,
                    ignore = copytreeIgnore)

    self.cwd = joinpath(tmptestDir, os.sep.join(testPathParts[2:]))
    self.projectConf = bconfloader.load(dirpath = self.cwd)
    self.origProjectDir = currentPrjDir

    return testPath

def processConfManagerWithCLI(testSuit, cmdLine):
    cmdLine = list(cmdLine)
    cmdLine.insert(0, APPNAME)

    try:
        if testSuit.cmdLine == cmdLine:
            return testSuit.confManager
    except AttributeError:
        pass

    noBuildConf = False
    cmd = starter.handleCLI(cmdLine, noBuildConf, None)
    starter.adjustCliDirPaths(testSuit.cwd, cmd.args)

    def cliOptsHandler(defaults):
        cmd = starter.handleCLI(cmdLine, noBuildConf, defaults)
        starter.adjustCliDirPaths(testSuit.cwd, cmd.args)
        return cmd

    bconfDir = testSuit.cwd
    confManager = BuildConfManager(bconfDir, clivars = cmd.args,
                                        clihandler = cliOptsHandler)
    testSuit.confManager = confManager
    testSuit.confPaths = confManager.root.confPaths

    cmd = starter.handleCLI(cmdLine, False, confManager.root.cliopts)

    testSuit.cmdLine = cmdLine
    db.useformat(confManager.root.general['db-format'])
    return testSuit.confManager

def getTaskEnv(testSuit, taskName):
    bconf = testSuit.confManager.root
    buildtype = bconf.selectedBuildType
    cachedir = bconf.confPaths.zmcachedir

    taskVariant = assist.makeTaskVariantName(buildtype, taskName)
    cachedir = bconf.confPaths.zmcachedir
    cachePath = assist.makeTasksCachePath(cachedir, buildtype)

    tasksData = db.loadFrom(cachePath)
    taskenvs = tasksData['taskenvs']
    env = ConfigSet()
    env.table = taskenvs[taskVariant]
    return env

def getTargetPattern(env, features):
    kind = 'file'
    fileNamePattern = '%s'
    for feature in features:
        # find pattern via brute force :)
        key = feature + '_PATTERN'
        if key not in env:
            continue
        fileNamePattern = env[key]
        if feature.endswith('program'):
            kind = 'exe'
        elif feature.endswith('shlib'):
            kind = 'shlib'
        elif feature.endswith('stlib'):
            kind = 'stlib'

    return fileNamePattern, kind

def getCachedTargetPattern(testSuit, taskName, features):

    cache = _cache[testSuit.origProjectDir]['target-patterns']
    result = cache.get(taskName)
    if not result:
        env = getTaskEnv(testSuit, taskName)
        cache[taskName] = result = getTargetPattern(env, features)

    return result

def handleTaskFeatures(testSuit, taskParams):
    assist.detectTaskFeatures(taskParams)
    assert isinstance(taskParams['features'], list)

def getBuildTasks(confManager):
    tasks = {}
    for bconf in confManager.configs:
        tasks.update(bconf.tasks)
        defaultLibVersion = bconf.defaultLibVersion
        for taskParams in tasks.values():
            if defaultLibVersion and 'ver-num' not in taskParams:
                taskParams['ver-num'] = defaultLibVersion
    return tasks

def obtainBuildTargets(testSuit, cmdLine, withTests = False):

    def makeConfDict(conf, deep):
        result = AutoDict()
        _conf = AutoDict(vars(conf))
        for k in KNOWN_CONF_PARAM_NAMES:
            if deep:
                result[k] = deepcopy(_conf[k])
            else:
                result[k] = copy(_conf[k])
        return result

    _conf = makeConfDict(testSuit.projectConf, deep = True)

    result = {}

    processConfManagerWithCLI(testSuit, cmdLine)
    confManager = testSuit.confManager
    buildtype = confManager.root.selectedBuildType
    buildout = confManager.root.confPaths.buildout
    isWindows = PLATFORM == 'windows'
    isLinux = PLATFORM == 'linux'

    tasks = getBuildTasks(confManager)
    for taskName, taskParams in tasks.items():

        handleTaskFeatures(testSuit, taskParams)
        features = taskParams['features']

        if not withTests and 'test' in features:
            # ignore test tasks
            continue

        if not [ x for x in features if x in TASK_TARGET_FEATURES ]:
            # use only TASK_TARGET_FEATURES
            continue

        info = {}
        fpattern, targetKind = getCachedTargetPattern(testSuit, taskName, features)
        target = taskParams.get('target', taskName)
        targetdir = joinpath(buildout, buildtype)

        info['targets-required'] = []
        info['targets-one-of'] = []

        if targetKind == 'shlib':
            targetpath = joinpath(targetdir, fpattern % target)
            verNum = taskParams.get('ver-num', None)
            if verNum:
                nums = verNum.split('.')
                alttarget = target + '-' + nums[0]
                info['targets-one-of'] = [targetpath,
                    joinpath(targetdir, fpattern % alttarget)]

                if isLinux:
                    targetpath1 = targetpath + '.' + nums[0]
                    targetpath2 = targetpath + '.' + verNum
                    info['targets-required'] += [targetpath1, targetpath2]

                elif targetpath.endswith('.dylib'):
                    fname = fpattern % (target + '.' + nums[0])
                    info['targets-required'].append(joinpath(targetdir, fname))
                    fname = fpattern % (target + '.' + verNum)
                    info['targets-required'].append(joinpath(targetdir, fname))
            else:
                info['targets-required'].append(targetpath)

            if isWindows:
                targetpath = joinpath(targetdir, '%s.lib' % target)
                info['targets-required'].append(targetpath)
        else:
            targetpath = joinpath(targetdir, fpattern % target)
            info['targets-required'].append(targetpath)

        info['kind'] = targetKind
        result[taskName] = info

     # check original buildconf was not changed
    assert _conf == makeConfDict(testSuit.projectConf, deep = False)

    return result

def checkBuildTargets(targets, resultExists, fakeBuild = False):

    for targetsInfo in targets.values():

        kind = targetsInfo['kind']
        targets = targetsInfo['targets-required']
        for target in targets:
            assert isfile(target) == resultExists

        if kind == 'exe' and resultExists and not fakeBuild:
            assert len(targets) == 1
            assert os.access(targets[0], os.X_OK)

        targets = targetsInfo['targets-one-of']
        if targets:
            if resultExists:
                assert any(isfile(x) for x in targets)
            else:
                assert all(not isfile(x) for x in targets)

def checkBuildResults(testSuit, cmdLine, resultExists, withTests = False,
                                                       fakeBuild = False):

    targets = obtainBuildTargets(testSuit, cmdLine, withTests)
    checkBuildTargets(targets, resultExists, fakeBuild)

_RE_ANY_TASK = re.compile(r"\s*\[\s*-?\d+/(\d+)\s*\]\s+.+")
_RE_COMPILE_TASK = re.compile(r"\s*\[\s*-?\d+/\d+\s*\]\s+Compiling\s+([\w\d]+.+)", re.U)
_RE_LINK_TASK = re.compile(r"\s*\[\s*-?\d+/\d+\s*\]\s+Linking\s+.+\%s(lib)?([\w\-\s]+)" % os.sep, re.U)
_RE_RUNCMD_TASK = re.compile(r"\s*\[\s*-?\d+/\d+\s*\]\s+Running\s+command\s+.*?\'([\w\s.\-]+)\'$", re.U)
_RE_TEST_TASK = re.compile(r"\s*Running\s+test:\s+\'([\w\s.\-]+)\'$", re.U)

def gatherEventsFromOutput(output):

    CMD_NAMES = ('build', 'test')

    events = {}
    cmdEvents = []
    cmdOutput = []
    taskRealCount = 0
    taskMaxCount = 0
    cmdIndexes = defaultdict(dict)

    def findCmdEnd(line):
        for cmdName in CMD_NAMES:
            m = re.match(r"'%s'\s+finished" % cmdName, line)
            if m:
                return cmdName
        return None

    for line in output.splitlines():
        cmdName = findCmdEnd(line)
        if cmdName:
            events[cmdName] = dict(
                events = cmdEvents,
                indexes = cmdIndexes,
                output = cmdOutput,
                taskRealCount = taskRealCount,
                taskMaxCount = taskMaxCount,
            )
            cmdEvents = []
            cmdOutput = []
            taskRealCount = 0
            taskMaxCount = 0
            cmdIndexes = defaultdict(dict)
            continue

        isWafTaskStarting = False
        m = _RE_ANY_TASK.search(line)
        if m:
            taskRealCount += 1
            taskMaxCount = int(m.group(1))
            isWafTaskStarting = True

        m = _RE_COMPILE_TASK.search(line)
        if m:
            task = m.group(1).replace('\\', '/')
            cmdEvents.append(['compiling', task])
            cmdIndexes['compiling'][task] = len(cmdEvents) - 1
            continue

        m = _RE_LINK_TASK.search(line)
        if m:
            task = m.group(2)
            cmdEvents.append(['linking', task])
            cmdIndexes['linking'][task] = len(cmdEvents) - 1
            continue

        m = _RE_RUNCMD_TASK.search(line)
        if m:
            task = m.group(1)
            cmdEvents.append(['running', task])
            cmdIndexes['running'][task] = len(cmdEvents) - 1
            continue

        m = _RE_TEST_TASK.search(line)
        if m:
            task = m.group(1)
            cmdEvents.append(['running', task])
            cmdIndexes['running'][task] = len(cmdEvents) - 1
            continue

        terminators = [r"^Waf:\s+"]
        if isWafTaskStarting or any(bool(re.match(expr, line)) for expr in terminators):
            continue

        cmdOutput.append(line)

    if cmdEvents:
        events['unknown'] = cmdEvents

    return events

def checkMsgInOutput(msg, output, count = None):
    if isinstance(output, list):
        output = '\n'.join(output)

    if not count:
        assert msg in output
    else:
        assert output.count(msg) == count
