# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = no-member, redefined-outer-name
# pylint: disable = attribute-defined-outside-init

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import pytest

from waflib import Context
from zm.constants import PLATFORM, CPU_ARCH
from zm.pyutils import maptype, stringtype
from zm.pathutils import PathsParam
from zm.autodict import AutoDict
from zm import cli, utils
from zm.buildconf.processing import Config, ConfManager
from zm.buildconf.scheme import KNOWN_TASK_PARAM_NAMES, EXPORTING_TASK_PARAMS
from zm.buildconf.select import clearLocalCache as clearSelectLocalCache
from zm import features
from tests.common import asRealConf

joinpath = os.path.join

class BConfManager(ConfManager):

    def __init__(self, topdir, clivars, buildconf):
        self._buildconfs = {}
        self.setBuildConf(topdir, buildconf)
        super().__init__(topdir, clivars)

    def setBuildConf(self, dirpath, buildconf):
        self._buildconfs[dirpath] = buildconf

    def makeConfig(self, dirpath, parent = None):

        buildconf = self._buildconfs[dirpath]

        index = len(self._orderedConfigs)
        self._configs[dirpath] = index
        bconf = Config(buildconf, self._clivars, parent)
        self._orderedConfigs.append(bconf)

        return super().makeConfig(dirpath, parent)

PARAM_TEST_VALUES = {
    'toolchain' : ['gcc', 'clang', 'auto-c'],
    'target'    : ['test-target', 'super-target', 'a-target'],
    'source'    : ['test.c', 'test.c main.c', ['test.c', 'mmain.c']],
    'includes'  : ['inc1', 'inc1 inc2', ['inc1', 'inc3']],
    'export-includes'  : ['inc1', 'inc1 inc2', ['inc1', 'inc3']],
    'export'  : [ 'defines', 'defines includes', ['defines', 'includes'] ],
    'run' : [ {}, {'cmd': 'ls'}, {'cmd': 'ls -la'}],
    'objfile-index' : [1, 2, 3],
}

def _setup():
    paramNames = [x[:x.rfind('.')] for x in KNOWN_TASK_PARAM_NAMES if x.endswith('.select')]
    # param 'configure' is removed at the end of 'configure'
    paramNames.remove('configure')
    for name in paramNames:
        if name not in PARAM_TEST_VALUES:
            PARAM_TEST_VALUES[name] = ['val1', 'val1 val2', ['val3', 'val4']]
    return paramNames, PARAM_TEST_VALUES

TASKPARAM_NAMES, PARAM_TEST_VALUES = _setup()

@pytest.mark.usefixtures("unsetEnviron")
@pytest.fixture
def cfgctx(cfgctx):

    cfgCtx = cfgctx

    def execute():
        # pylint: disable = protected-access
        cfgCtx._prepareBConfs()
        cfgCtx.preconfigure()
        cfgCtx.recurse([Context.run_dir])
    cfgCtx.execute = execute

    return cfgCtx

@pytest.fixture(params = TASKPARAM_NAMES)
def paramName(request):
    return request.param

def checkExpectedDefault(taskParams, paramName, expected):
    result = taskParams[paramName]
    assert utils.toList(result) == utils.toList(expected)

def checkExpectedToolchain(taskParams, paramName, expected):
    result = taskParams[paramName]
    assert result == [expected]

def checkExpectedTarget(taskParams, paramName, expected):
    result = taskParams[paramName]
    assert os.path.basename(result) == expected

def checkExpectedSource(taskParams, paramName, expected):
    result = taskParams[paramName]
    assert utils.toList(result[0]['paths']) == utils.toList(expected)

def checkExpectedIncludes(taskParams, paramName, expected):
    result = taskParams[paramName]
    if isinstance(result, maptype):
        result = result['paths']
    elif isinstance(result, PathsParam):
        result = result.relpaths()
    result = [x for x in utils.toList(result) if x != '.']
    assert result == utils.toList(expected)

checkExpectedExportIncludes = checkExpectedIncludes

def checkExpectedExport(taskParams, _, expected):

    if isinstance(expected, stringtype):
        expectedParams = utils.toList(expected)
    elif isinstance(expected, (list, tuple)):
        expectedParams = expected
    else:
        assert False

    for param in EXPORTING_TASK_PARAMS:
        exportName = 'export-%s' % param
        if param in expectedParams:
            assert taskParams[exportName]
        else:
            assert not taskParams.get(exportName)

def checkExpectedLibpath(taskParams, paramName, expected):
    result = taskParams[paramName]
    assert [os.path.basename(x) for x in result]  == utils.toList(expected)

def checkExpectedStlibpath(taskParams, paramName, expected):
    result = taskParams[paramName]
    assert [os.path.basename(x) for x in result]  == utils.toList(expected)

def checkExpectedRun(taskParams, paramName, expected):
    result = taskParams[paramName]
    for name in expected:
        assert result[name] == expected[name]

def _postBuildconfSetup(buildconf, paramName):

    if paramName in ('monitlibs', 'monitstlibs'):
        paramTestValues = PARAM_TEST_VALUES[paramName]
        libsparamName = paramName[5:]

        libsValues = [ utils.toList(x) for x in paramTestValues ]
        values = set()
        for vals in libsValues:
            values.update(vals)
        libsValues = list(values)

        for params in buildconf.tasks.values():
            params[libsparamName] = libsValues

def getFixtureCase1(_, testingBuildConf, paramName):

    # select 'linux'

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    selectableParamName = "%s.select" % paramName
    buildconf.tasks.mytask[selectableParamName] = {
        'default' : paramTestValues[0],
        'linux' : paramTestValues[1],
        'darwin' : paramTestValues[2],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = { 'mytask' : paramTestValues[1] }

    return paramName, buildconf, expected

def getFixtureCase2(_, testingBuildConf, paramName):

    # select 'default'

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    selectableParamName = "%s.select" % paramName
    buildconf.tasks.mytask[selectableParamName] = {
        'default' : paramTestValues[0],
        'windows' : paramTestValues[1],
        'darwin' : paramTestValues[2],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = { 'mytask' : paramTestValues[0] }

    return paramName, buildconf, expected

def getFixtureCase3(_, testingBuildConf, paramName):

    # select 'default' from non-select

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    buildconf.tasks.mytask[paramName] = paramTestValues[1]

    selectableParamName = "%s.select" % paramName
    buildconf.tasks.mytask[selectableParamName] = {
        'windows' : paramTestValues[2],
        'darwin' : paramTestValues[0],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = { 'mytask' :paramTestValues[1] }

    return paramName, buildconf, expected

def getFixtureCase4(_, testingBuildConf, paramName):

    # select 'linux' and 'task1' or 'default'

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    buildconf.tasks.task1 = {
        'features' : ['c', 'cprogram'],
    }

    buildconf.conditions = {
        'task1' : { 'task': 'task1',}
    }

    selectableParamName = "%s.select" % paramName
    buildconf.buildtypes.debug[selectableParamName] = {
        'default' : paramTestValues[0],
        'linux and task1' : paramTestValues[1],
        'windows' : paramTestValues[2],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = {
        'mytask': paramTestValues[0],
        'task1': paramTestValues[1],
    }

    return paramName, buildconf, expected

def getFixtureCase5(_, testingBuildConf, paramName):

    # select 'CPU_ARCH' or 'default'

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    buildconf.tasks.task1 = {
        'features' : ['c', 'cprogram'],
    }

    buildconf.conditions = {
        'task1' : { 'task': 'task1',},
        'x64' : { 'cpu-arch': CPU_ARCH },
        'arm' : { 'cpu-arch': 'arm' },
    }

    selectableParamName = "%s.select" % paramName
    buildconf.buildtypes.debug[selectableParamName] = {
        'default' : paramTestValues[0],
        'x64 and task1' : paramTestValues[1],
        'arm' : paramTestValues[2],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = {
        'mytask': paramTestValues[0],
        'task1': paramTestValues[1],
    }

    return paramName, buildconf, expected

def getFixtureCase6(monkeypatch, testingBuildConf, paramName):

    # select by env

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    buildconf.tasks.task1 = {
        'features' : ['c', 'cprogram'],
    }

    buildconf.conditions = {
        'myenv-task1' : {
            'task': 'task1',
            'env': {
                'TVAR1' : 'true',
                'TVAR2' : '3',
            },
        },
        'myenv2' : {
            'env': {
                'TVAR3' : 'test',
            },
        },
    }

    monkeypatch.setenv('TVAR1', 'true')
    monkeypatch.setenv('TVAR2', '3')

    selectableParamName = "%s.select" % paramName
    buildconf.buildtypes.debug[selectableParamName] = {
        'default' : paramTestValues[0],
        'myenv-task1' : paramTestValues[1],
        'myenv2' : paramTestValues[2],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = {
        'mytask': paramTestValues[0],
        'task1': paramTestValues[1],
    }

    return paramName, buildconf, expected

def getFixtureCase7(_, testingBuildConf, paramName):

    # select by 'toolchain'

    buildconf = testingBuildConf
    paramTestValues = PARAM_TEST_VALUES[paramName]

    if paramName == 'toolchain':
        # stub
        buildconf.tasks.mytask[paramName] = paramTestValues[0]
        expected = { 'mytask' :paramTestValues[0] }
        return paramName, buildconf, expected

    buildconf.tasks.task1 = {
        'features' : ['c', 'cprogram'],
    }

    buildconf.conditions = {
        'task1' : { 'task': 'task1',},
    }

    selectableParamName = "%s.select" % paramName
    buildconf.buildtypes.debug['toolchain'] = 'clang'
    buildconf.buildtypes.debug[selectableParamName] = {
        'default' : paramTestValues[0],
        'clang and task1' : paramTestValues[1],
        'gcc' : paramTestValues[2],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = {
        'mytask': paramTestValues[0],
        'task1': paramTestValues[1],
    }

    return paramName, buildconf, expected

def getFixtureCase8(_, testingBuildConf, paramName):

    # select by 'buildtype'

    paramTestValues = PARAM_TEST_VALUES[paramName]
    buildconf = testingBuildConf

    buildconf.tasks.mytask[paramName] = paramTestValues[1]

    buildconf.buildtypes = {
        'dbg' : {},
        'release': {},
        'default': 'release',
    }

    buildconf.tasks.task1 = {
        'features' : ['c', 'cprogram'],
    }

    buildconf.conditions = {
        'debug' : {
            'buildtype': 'dbg',
        },
    }

    selectableParamName = "%s.select" % paramName
    buildconf.tasks.mytask[selectableParamName] = {
        'debug' : paramTestValues[2],
        'release' : paramTestValues[0],
        'default': paramTestValues[1],
    }
    buildconf.tasks.task1[selectableParamName] = {
        'debug' : paramTestValues[2],
        'default': paramTestValues[1],
    }
    _postBuildconfSetup(buildconf, paramName)
    expected = {
        'mytask' :paramTestValues[0],
        'task1' :paramTestValues[1],
    }

    return paramName, buildconf, expected

def getParamTestCases():
    i = 1
    result = dict(params = [], ids = [])
    while True:
        funcName = "getFixtureCase%d" % i
        if funcName not in globals():
            break
        result['params'].append(globals()[funcName])
        result['ids'].append(str(i))
        i += 1

    return result

@pytest.fixture(**getParamTestCases())
def paramFixtureFunc(request):
    return request.param

@pytest.fixture
def paramfixture(monkeypatch, testingBuildConf, paramName, paramFixtureFunc):
    testingBuildConf.tasks.mytask = {
        'features' : ['c', 'cprogram'],
    }
    return paramFixtureFunc(monkeypatch, testingBuildConf, paramName)

@pytest.mark.skipif(PLATFORM != 'linux', reason = "It's enough to test on linux only")
def testParam(cfgctx, monkeypatch, paramfixture):

    # it's necessary because 'id' is used for each bconf in cache and
    # due to removing old objects by python garbage collector some new
    # bconf objects can have an old id
    clearSelectLocalCache()

    ctx = cfgctx

    paramname, buildconf, expected = paramfixture

    clicmd = cli.ParsedCommand(name = 'build', args = AutoDict(), orig = [])
    monkeypatch.setattr(cli, 'selected', clicmd)

    bconfDir = ctx.path.abspath()
    clivars = None
    buildconf = asRealConf(buildconf, bconfDir)
    bconfManager = BConfManager(bconfDir, clivars, buildconf)
    setattr(ctx, 'bconfManager', bconfManager)

    tasksList = [bconf.tasks for bconf in bconfManager.configs]
    features.loadFeatures(tasksList)

    ctx.execute()

    funcName = "checkExpected%s" % ''.join([x.capitalize() for x in paramname.split('-')])
    checkExpected = globals().get(funcName)
    if checkExpected is None:
        checkExpected = checkExpectedDefault
    bconf = bconfManager.root
    for taskParams in bconf.tasks.values():
        _expected = expected[taskParams['name']]
        checkExpected(taskParams, paramname, _expected)
