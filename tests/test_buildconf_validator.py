# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = no-member, attribute-defined-outside-init

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from collections import defaultdict
import pytest
from zm.error import *
from zm.constants import KNOWN_PLATFORMS
from zm.pyutils import stringtype
from zm.buildconf.scheme import KNOWN_CONF_ACTIONS
from zm.buildconf.validator import Validator
import tests.common as cmn

validator = Validator()

class FakeBuildConf:
    __name__ = 'testconf'
    __file__ = os.path.join(os.getcwd(), 'fakeconf.py')

class TestSuite(object):

    def saveparam(func):
        # pylint: disable = no-self-argument

        def wrapper(self, *args, **kwargs):

            confnode = kwargs.get('confnode') or args[1]
            params = kwargs.get('param') or kwargs.get('paramNames') or args[2]
            if isinstance(params, stringtype):
                params = [params]
            old = {}
            for param in [x for x in params if x in confnode]:
                old[param] = confnode[param]

            try:
                # pylint: disable = not-callable
                func(self, *args, **kwargs)
            finally:
                for k, v in old.items():
                    confnode[k] = v
        return wrapper

    def _validateBoolValues(self, buildconf, confnode, param, _ = None):
        confnode[param] = True
        validator.validate(buildconf)
        confnode[param] = False
        validator.validate(buildconf)

    def _validateIntValues(self, buildconf, confnode, param, validVals = None):
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

    def _validateStrValues(self, buildconf, confnode, param, validVals = None):
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

    def _validateListOfStrsValues(self, buildconf, confnode, param, validVals = None):
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

    def _validateDictValues(self, buildconf, confnode, param, validVals = None):
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

    def _validateFuncValues(self, buildconf, confnode, param, validVals = None):
        if not validVals:
            def f():
                pass
            confnode[param] = f
            validator.validate(buildconf)
            confnode[param] = lambda: 1
            validator.validate(buildconf)
        else:
            for v in validVals:
                confnode[param] = v
                validator.validate(buildconf)

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

    @saveparam
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

    @saveparam
    def _checkParamsAsStr(self, buildconf, confnode, paramNames, validVals = None):
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

    @saveparam
    def _checkParamsAsInt(self, buildconf, confnode, paramNames, validVals = None):
        for param in paramNames:
            confnode[param] = cmn.randomstr()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomstr()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomint(), cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateIntValues(buildconf, confnode, param, validVals)

    @saveparam
    def _checkParamsAsFunc(self, buildconf, confnode, paramNames):
        for param in paramNames:
            confnode[param] = cmn.randomstr()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomstr()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomint(), cmn.randomint()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateFuncValues(buildconf, confnode, param)

    @saveparam
    def _checkParamsAsListOfStrs(self, buildconf, confnode, paramNames, validVals = None):
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
            confnode[param] = [cmn.randomint(), cmn.randomint(), cmn.randomstr()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateListOfStrsValues(buildconf, confnode, param, validVals)

    @saveparam
    def _checkParamsAsStrOrListOfStrs(self, buildconf, confnode, paramNames, validVals = None):
        for param in paramNames:
            confnode[param] = {}
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = cmn.randomint()
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            confnode[param] = [cmn.randomint(), cmn.randomint(), cmn.randomstr()]
            with pytest.raises(ZenMakeConfTypeError):
                validator.validate(buildconf)
            self._validateStrValues(buildconf, confnode, param, validVals)
            self._validateListOfStrsValues(buildconf, confnode, param, validVals)

    @saveparam
    def _checkParamsAs(self, buildconf, confnode, paramNames, validTypesAndVals):
        validTypes = set(validTypesAndVals.keys())
        allTypes = set(('int', 'bool', 'str', 'list', 'list-of-strs', 'dict', 'func'))
        invalidTypes = allTypes - validTypes
        if 'list' in invalidTypes and  'list-of-strs' in validTypes:
            invalidTypes.remove('list')

        def testfunc():
            return True

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
            'dict' : { 'valid' : [ {}, defaultdict(list) ] },
            'func' : { 'valid' : [ testfunc ] },
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
        self._checkParamsAsStr(buildconf, confnode, ['target'])

        validVals = ['2', '1.0', '4.5.6']
        self._checkParamsAsStr(buildconf, confnode, ['ver-num'], validVals)

        paramNames = (
            'features', 'libs', 'libpath', 'stlibs', 'stlibpath', 'rpath',
            'use', 'includes', 'cflags', 'cxxflags', 'cppflags',
            'linkflags', 'defines',
        )
        self._checkParamsAsStrOrListOfStrs(buildconf, confnode, paramNames)

        validTypesAndVals = {
            'str' : [],
            'list-of-strs' : [],
            'dict' : {
                'incl' :       { 'type': 'str' },
                'excl' :       { 'type': 'str' },
                'ignorecase' : { 'type': 'bool' },
            }
        }
        self._checkParamsAs(buildconf, confnode, ['source'], validTypesAndVals)

        confnode['config-actions'] = cmn.randomint()
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode['config-actions'] = cmn.randomstr()
        with pytest.raises(ZenMakeConfTypeError):
            validator.validate(buildconf)
        confnode['config-actions'] = tuple()
        validator.validate(buildconf)
        confnode['config-actions'] = []
        validator.validate(buildconf)

        confnode['config-actions'] = [ { 'do' : 'check-headers', } ]
        validator.validate(buildconf)
        self._checkParamsAsStr(buildconf, confnode['config-actions'][0],
                               ['do'], list(KNOWN_CONF_ACTIONS))
        self._checkParamsAsStrOrListOfStrs(buildconf, confnode['config-actions'][0],
                               ['names'])
        self._validateBoolValues(buildconf, confnode['config-actions'][0], 'mandatory')

        confnode['config-actions'] = [ { 'do' : 'check-libs', } ]
        validator.validate(buildconf)
        self._checkParamsAsStr(buildconf, confnode['config-actions'][0],
                               ['do'], list(KNOWN_CONF_ACTIONS))
        self._validateBoolValues(buildconf, confnode['config-actions'][0], 'autodefine')
        self._validateBoolValues(buildconf, confnode['config-actions'][0], 'fromtask')

        confnode['run'] = {}
        validTypesAndVals = { 'str' : None, 'func' : None, }
        self._checkParamsAs(buildconf, confnode['run'], ['cmd'], validTypesAndVals)
        self._checkParamsAsStr(buildconf, confnode['run'], ['cwd'])
        self._checkParamsAsInt(buildconf, confnode['run'], ['repeat', 'timeout'])
        self._validateBoolValues(buildconf, confnode['run'], 'shell')
        self._checkParamAsDict(buildconf, confnode['run'], 'env')

    def testValidateParamStrs(self):

        for param in ('buildroot', 'realbuildroot', 'startdir'):
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
        with pytest.raises(ZenMakeConfError):
            validator.validate(buildconf)

    def testValidateParamProject(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'project')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'project', {})

        self._checkParamsAsStr(buildconf, buildconf.project, ['name'])
        self._checkParamsAsStr(buildconf, buildconf.project, ['version'])

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
        buildconf.buildtypes = {
            btypeNames[0] : {},
            btypeNames[3] : {},
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

    def testValidateParamPlatforms(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsDict(buildconf, 'platforms')

        buildconf = FakeBuildConf()
        setattr(buildconf, 'platforms', {
            KNOWN_PLATFORMS[0] + cmn.randomstr() : {}
        })
        with pytest.raises(ZenMakeConfError):
            validator.validate(buildconf)
        setattr(buildconf, 'platforms', {
            KNOWN_PLATFORMS[0] + cmn.randomstr() : {},
            KNOWN_PLATFORMS[1] + cmn.randomstr() : {},
        })
        with pytest.raises(ZenMakeConfError):
            validator.validate(buildconf)
        setattr(buildconf, 'platforms', {})
        for _platform in KNOWN_PLATFORMS:
            buildconf.platforms[_platform] = {}
        validator.validate(buildconf)

        buildconf = FakeBuildConf()
        setattr(buildconf, 'platforms', {})
        for _platform in KNOWN_PLATFORMS:
            buildconf.platforms[_platform] = {}
            self._checkParamsAsStrOrListOfStrs(
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

    def testValidateParamByfilter(self):

        buildconf = FakeBuildConf()
        self._checkAttrAsList(buildconf, 'byfilter')

        setattr(buildconf, 'byfilter', [])
        buildconf.byfilter = [ {} ]
        validator.validate(buildconf)
        self._checkParamAsDict(buildconf, buildconf.byfilter[0], 'for')
        self._checkParamAsDict(buildconf, buildconf.byfilter[0], 'set')

        buildconf.byfilter = [ { 'for' : {}, }, { 'for' : {}, 'set' : {} } ]
        validator.validate(buildconf)
        self._checkParamsAsStrOrListOfStrs(buildconf, buildconf.byfilter[1]['for'],
                               ['task', 'buildtype', 'platform'])
        self._checkTaskScheme(buildconf, buildconf.byfilter[1]['set'])
