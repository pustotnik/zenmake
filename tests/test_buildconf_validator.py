# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from collections import defaultdict
import shutil
import pytest
from zm.error import *
from zm.constants import KNOWN_PLATFORMS
import tests.common as cmn
from zm.buildconf.validator import Validator, KNOWN_TOOLCHAIN_KINDS

validator = Validator()

class FakeBuildConf:
    __name__ = 'testconf'

class TestSuite(object):

    def _validateBoolValues(self, buildconf, confnode, param, validVals = []):
        confnode[param] = True
        validator.validate(buildconf)
        confnode[param] = False
        validator.validate(buildconf)

    def _validateIntValues(self, buildconf, confnode, param, validVals = []):
        if not validVals:
            confnode[param] = cmn.randomint()
            validator.validate(buildconf)
        else:
            invalid = cmn.randomint()
            while invalid in validVals:
                #FIXME: to think up more fast and stable solution
                invalid = cmn.randomint()
            confnode[param] = invalid
            with pytest.raises(ZenMakeConfValueError):
                validator.validate(buildconf)
            for v in validVals:
                confnode[param] = v
                validator.validate(buildconf)

    def _validateStrValues(self, buildconf, confnode, param, validVals = []):
        if not validVals:
            confnode[param] = cmn.randomstr()
            validator.validate(buildconf)
        else:
            invalid = validVals[0] + cmn.randomstr()
            while invalid in validVals:
                invalid = cmn.randomstr()
            confnode[param] = invalid
            with pytest.raises(ZenMakeConfValueError):
                validator.validate(buildconf)
            for v in validVals:
                confnode[param] = v
                validator.validate(buildconf)

    def _validateListOfStrsValues(self, buildconf, confnode, param, validVals = []):
        if not validVals:
            confnode[param] = [cmn.randomstr(), cmn.randomstr()]
            validator.validate(buildconf)
            confnode[param] = (cmn.randomstr(), cmn.randomstr())
            validator.validate(buildconf)
        else:
            invalid = str(validVals[0]) + cmn.randomstr()
            confnode[param] = [invalid]
            with pytest.raises(ZenMakeConfValueError):
                validator.validate(buildconf)
            confnode[param] = validVals
            validator.validate(buildconf)

    def _validateDictValues(self, buildconf, confnode, param, validVals = {}):
        if not validVals:
            confnode[param] = { cmn.randomstr() : cmn.randomint() }
            validator.validate(buildconf)
        else:
            for k, v in validVals.items():
                _type = v['type']
                methodName = ''.join([x.capitalize() for x in _type.split('-')])
                methodName = '_validate%sValues' % methodName
                validateValues = getattr(self, methodName)
                confnode[param] = {}
                validateValues(buildconf, confnode[param], k)

    def _checkAttrAsDict(self, buildconf, attrName):
        setattr(buildconf, attrName, cmn.randomint())
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, attrName, cmn.randomstr())
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, attrName, [])
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, attrName, {})
        validator.validate(buildconf)

    def _checkAttrAsList(self, buildconf, attrName):
        setattr(buildconf, attrName, cmn.randomint())
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, attrName, cmn.randomstr())
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, attrName, {})
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, attrName, [])
        validator.validate(buildconf)
        setattr(buildconf, attrName, tuple())
        validator.validate(buildconf)

    def _checkParamAsDict(self, buildconf, confnode, paramName):
        confnode[paramName] = cmn.randomint()
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode[paramName] = cmn.randomstr()
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode[paramName] = []
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode[paramName] =  {}
        validator.validate(buildconf)

    def _checkParamsAsStr(self, buildconf, confnode, paramNames, validVals = []):
        for param in paramNames:
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomstr(), cmn.randomstr()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateStrValues(buildconf, confnode, param, validVals)

    def _checkParamsAsListOfStrs(self, buildconf, confnode, paramNames, validVals = []):
        for param in paramNames:
            confnode[param] = {}
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = cmn.randomstr()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomstr(), cmn.randomint(), cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateListOfStrsValues(buildconf, confnode, param, validVals)

    def _checkParamsAsStrOrListOfStrs(self, buildconf, confnode, paramNames, validVals = []):
        for param in paramNames:
            confnode[param] = {}
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomstr(), cmn.randomint(), cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateStrValues(buildconf, confnode, param, validVals)
            self._validateListOfStrsValues(buildconf, confnode, param, validVals)

    def _checkParamsAs(self, buildconf, confnode, paramNames, validTypesAndVals):
        validTypes = set(validTypesAndVals.keys())
        allTypes = set(('int', 'bool', 'str', 'list', 'list-of-strs', 'dict'))
        invalidTypes = allTypes - validTypes
        if 'list' in invalidTypes and  'list-of-strs' in validTypes:
            invalidTypes.remove('list')

        typeValues = {
            'bool' : { 'valid' : [True, False] },
            'int' : { 'valid' : [cmn.randomint(), cmn.randomint()] },
            'str' : { 'valid' : [cmn.randomstr(), cmn.randomstr()] },
            'list' : { 'valid' : [ [], [cmn.randomint()]] },
            'list-of-strs' : {
                'valid' : [
                    [], [cmn.randomstr(), cmn.randomstr()],
                    tuple(), (cmn.randomstr(), cmn.randomstr())
                ],
                'invalid' : [
                    [cmn.randomstr(), cmn.randomint()],
                    (cmn.randomint(), cmn.randomstr())
                ],
            },
            'dict' : { 'valid' : [ {}, defaultdict(list) ] }
        }
        for param in paramNames:
            for t in invalidTypes:
                for val in typeValues[t]['valid']:
                    confnode[param] = val
                    with pytest.raises(ZenMakeConfTypeError):
                        validator.validate(buildconf)
            for t in validTypes:
                for val in typeValues[t]['valid']:
                    confnode[param] = val
                    validator.validate(buildconf)
                if 'invalid' not in typeValues[t]:
                    continue
                for val in typeValues[t]['invalid']:
                    confnode[param] = val
                    with pytest.raises(ZenMakeConfTypeError):
                        validator.validate(buildconf)

            for t, validVals in validTypesAndVals.items():
                methodName = ''.join([x.capitalize() for x in t.split('-')])
                validateValues = getattr(self, '_validate%sValues' % methodName)
                validateValues(buildconf, confnode, param, validVals)

    def _checkTaskScheme(self, buildconf, confnode):

        self._validateBoolValues(buildconf, confnode, 'normalize-target-name')

        paramNames = (
            'target', 'ver-num',
        )
        self._checkParamsAsStr(buildconf, confnode, paramNames)

        self._checkParamsAsStr(buildconf, confnode,
                               ['toolchain'], KNOWN_TOOLCHAIN_KINDS)

        paramNames = (
            'features', 'sys-libs', 'sys-lib-path', 'rpath', 'use', 'includes',
            'cflags', 'cxxflags', 'cppflags', 'linkflags', 'defines',
        )
        self._checkParamsAsStrOrListOfStrs(buildconf, confnode, paramNames)

        validTypesAndVals = {
            'str' : [],
            'list-of-strs' : [],
            'dict' : {
                'include' :    { 'type': 'str' },
                'exclude' :    { 'type': 'str' },
                'ignorecase' : { 'type': 'bool' },
            }
        }
        self._checkParamsAs(buildconf, confnode, ['source'], validTypesAndVals)

        confnode['conftests'] = cmn.randomint()
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode['conftests'] = cmn.randomstr()
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode['conftests'] = tuple()
        validator.validate(buildconf)
        confnode['conftests'] = []
        validator.validate(buildconf)

        confnode['conftests'] = [ { 'act' : 'check', } ]
        validator.validate(buildconf)
        self._checkParamsAsStr(buildconf, confnode['conftests'][0],
                               ['act', 'file'])
        self._checkParamsAsStrOrListOfStrs(buildconf, confnode['conftests'][0],
                               ['names'])
        self._validateBoolValues(buildconf, confnode['conftests'][0], 'mandatory')
        self._validateBoolValues(buildconf, confnode['conftests'][0], 'autodefine')

    def testValidateParamStrs(self):

        for param in ('buildroot', 'realbuildroot', 'srcroot'):
            buildconf = FakeBuildConf()
            setattr(buildconf, param, 11)
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            setattr(buildconf, param, cmn.randomstr())
            validator.validate(buildconf)

    def testValidateParamFeatures(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'features')

        setattr(buildconf, 'features', { 'autoconfig' : 1 })
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        setattr(buildconf, 'features', { 'autoconfig' : False })
        validator.validate(buildconf)
        setattr(buildconf, 'features', { 'autoconfig' : False, 'unknown': 1 })
        validator.validate(buildconf)

    def testValidateParamProject(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'project')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'project', {})
        paramNames = ('name', 'version', 'root')
        self._checkParamsAsStr(buildconf, buildconf.project, paramNames)

    def testValidateParamBuildtypes(self):

        btypeNames = [cmn.randomstr() for i in range(4)]

        #####
        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'buildtypes')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'buildtypes', {})
        for btype in btypeNames:
            buildconf.buildtypes[btype] = {}
            self._checkParamAsDict(buildconf, buildconf.buildtypes, btype)
        paramNames = ('default',)
        self._checkParamsAsStr(buildconf, buildconf.buildtypes,
                                paramNames, btypeNames)

        #####
        buildconf = FakeBuildConf()
        setattr(buildconf, 'buildtypes', {})
        setattr(buildconf, 'tasks', {})
        taskNames = [cmn.randomstr() for i in range(4)]
        buildconf.tasks[taskNames[0]] = {
            'buildtypes' : { btypeNames[0] : {} }
        }
        buildconf.tasks[taskNames[2]] = {
            'buildtypes' : { btypeNames[3] : {} }
        }
        buildconf.buildtypes['default'] = btypeNames[0]
        validator.validate(buildconf)
        buildconf.buildtypes['default'] = btypeNames[1]
        with pytest.raises(ZenMakeConfValueError):
            validator.validate(buildconf)
        buildconf.buildtypes['default'] = btypeNames[2]
        with pytest.raises(ZenMakeConfValueError):
            validator.validate(buildconf)
        buildconf.buildtypes['default'] = btypeNames[3]
        validator.validate(buildconf)

        #####
        buildconf = FakeBuildConf()
        setattr(buildconf, 'buildtypes', {
            'default': 'testbtype',
            'testbtype' : {}
        })
        self._checkTaskScheme(buildconf, buildconf.buildtypes['testbtype'])

    def testValidateParamToolchains(self):

        toolNames = [cmn.randomstr() for i in range(3)]

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'toolchains')

        setattr(buildconf, 'toolchains', { 1 : 1})
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)

        buildconf = FakeBuildConf()
        setattr(buildconf, 'toolchains', {})
        for tool in toolNames:
            buildconf.toolchains[tool] = {}
            validator.validate(buildconf)
            self._checkParamAsDict(buildconf, buildconf.toolchains, tool)
            self._checkParamsAsStr(buildconf, buildconf.toolchains[tool],
                               ['kind'], KNOWN_TOOLCHAIN_KINDS)
            paramNames = [cmn.randomstr() for i in range(10)]
            for param in paramNames:
                assert param != 'kind'
            self._checkParamsAsStr(buildconf, buildconf.toolchains[tool],
                                   paramNames)

        buildconf = FakeBuildConf()
        setattr(buildconf, 'toolchains', {})
        for tool in toolNames:
            buildconf.toolchains[tool] = {}
        setattr(buildconf, 'buildtypes', {
            'testbtype' : {}
        })

        self._checkParamsAsStr(buildconf, buildconf.buildtypes['testbtype'],
                               ['toolchain'], KNOWN_TOOLCHAIN_KINDS + toolNames)

    def testValidateParamPlatforms(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'platforms')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'platforms', {
            KNOWN_PLATFORMS[0] + cmn.randomstr() : {}
        })
        with pytest.raises(ZenMakeConfValueError):
            validator.validate(buildconf)
        setattr(buildconf, 'platforms', {
            KNOWN_PLATFORMS[0] + cmn.randomstr() : {},
            KNOWN_PLATFORMS[1] + cmn.randomstr() : {},
        })
        with pytest.raises(ZenMakeConfValueError):
            validator.validate(buildconf)
        setattr(buildconf, 'platforms', {})
        for _platform in KNOWN_PLATFORMS:
            buildconf.platforms[_platform] = {}
        validator.validate(buildconf)

        buildconf = FakeBuildConf()
        setattr(buildconf, 'platforms', {})
        for _platform in KNOWN_PLATFORMS:
            buildconf.platforms[_platform] = {}
            self._checkParamsAsListOfStrs(
                        buildconf, buildconf.platforms[_platform], ['valid'])
            self._checkParamsAsStr(
                        buildconf, buildconf.platforms[_platform], ['default'])

    def testValidateParamTasks(self):

        taskNames = [cmn.randomstr() for i in range(2)]

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'tasks')

        setattr(buildconf, 'tasks', { 1 : 1})
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)

        setattr(buildconf, 'tasks', {})
        for taskName in taskNames:
            buildconf.tasks[taskName] = {}
            validator.validate(buildconf)
            self._checkParamAsDict(buildconf, buildconf.tasks, taskName)
            self._checkTaskScheme(buildconf, buildconf.tasks[taskName])

    def testValidateParamMatrix(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsList(buildconf, 'matrix')

        setattr(buildconf, 'matrix', [])
        buildconf.matrix = [ {} ]
        validator.validate(buildconf)
        self._checkParamAsDict(buildconf, buildconf.matrix[0], 'for')
        self._checkParamAsDict(buildconf, buildconf.matrix[0], 'set')

        buildconf.matrix = [ { 'for' : {}, }, { 'for' : {}, 'set' : {} } ]
        validator.validate(buildconf)
        self._checkParamsAsStrOrListOfStrs(buildconf, buildconf.matrix[1]['for'],
                               ['task', 'buildtype', 'platform'])
        self._checkTaskScheme(buildconf, buildconf.matrix[1]['set'])