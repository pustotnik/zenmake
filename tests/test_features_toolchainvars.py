# coding=utf-8
#

# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = too-many-statements

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import pytest
from zm.error import ZenMakeError
from zm.features import ToolchainVars

LANGMAP = {
    'sys': {
        'c'   : 'CC',
        'cxx' : 'CXX',
        'asm' : 'AS',
        'd'   : 'DC',
    },
    'cfg' : {
        'c'   : 'CC',
        'cxx' : 'CXX',
        'asm' : 'AS',
        'd'   : 'D',
    },
}
SUPPORTED_LANGS = list(LANGMAP['sys'].keys())

def testAllSysFlagVars():
    gottenVars = ToolchainVars.allSysFlagVars()
    # to force covering of cache
    _gottenVars = ToolchainVars.allSysFlagVars()
    assert _gottenVars == gottenVars
    requiredVars = set([
        'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CFLAGS', 'LINKFLAGS',
        'ASFLAGS',
    ])
    assert requiredVars <= set(gottenVars)

def testAllCfgFlagVars():
    gottenVars = ToolchainVars.allCfgFlagVars()
    # to force covering of cache
    _gottenVars = ToolchainVars.allCfgFlagVars()
    assert _gottenVars == gottenVars
    requiredVars = set([
        'CPPFLAGS', 'CFLAGS', 'LINKFLAGS', 'CXXFLAGS',
        'LDFLAGS', 'DEFINES', 'ASFLAGS',
    ])
    assert requiredVars <= set(gottenVars)

def testAllLangs():
    assert sorted(ToolchainVars.allLangs()) == sorted(SUPPORTED_LANGS)

def testAllSysVarsToSetToolchain():
    gottenVars = ToolchainVars.allSysVarsToSetToolchain()
    # to force covering of cache
    _gottenVars = ToolchainVars.allSysVarsToSetToolchain()
    assert _gottenVars == gottenVars
    requiredVars = LANGMAP['sys'].values()
    assert sorted(requiredVars) == sorted(gottenVars)

def testAllCfgVarsToSetToolchain():
    gottenVars = ToolchainVars.allCfgVarsToSetToolchain()
    # to force covering of cache
    _gottenVars = ToolchainVars.allCfgVarsToSetToolchain()
    assert _gottenVars == gottenVars
    requiredVars = LANGMAP['cfg'].values()
    assert sorted(requiredVars) == sorted(gottenVars)

def testVarToSetToolchain():

    for tag in ('sys', 'cfg'):
        langMap = LANGMAP[tag]
        if tag == 'sys':
            testFunc = ToolchainVars.sysVarToSetToolchain
        else:
            testFunc = ToolchainVars.cfgVarToSetToolchain

        for lang in SUPPORTED_LANGS:
            gottenVar = testFunc(lang)
            assert gottenVar == langMap[lang]

        with pytest.raises(ZenMakeError):
            testFunc('')
        with pytest.raises(ZenMakeError):
            testFunc('invalid lang')
