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

SUPPORTED_LANGS = ['c', 'cxx', 'asm']

def testAllFlagVars():
    gottenVars = ToolchainVars.allFlagVars()
    # to force covering of cache
    _gottenVars = ToolchainVars.allFlagVars()
    assert _gottenVars == gottenVars
    requiredVars = set([
        'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CFLAGS', 'LINKFLAGS',
        'ASFLAGS',
    ])
    assert requiredVars <= set(gottenVars)

def testAllCfgEnvVars():
    gottenVars = ToolchainVars.allCfgEnvVars()
    # to force covering of cache
    _gottenVars = ToolchainVars.allCfgEnvVars()
    assert _gottenVars == gottenVars
    requiredVars = set([
        'CPPFLAGS', 'CFLAGS', 'LINKFLAGS', 'CXXFLAGS',
        'LDFLAGS', 'DEFINES', 'ASFLAGS',
    ])
    assert requiredVars <= set(gottenVars)

def testAllLangs():
    assert sorted(ToolchainVars.allLangs()) == sorted(SUPPORTED_LANGS)

def testAllVarsToSetToolchain():
    gottenVars = ToolchainVars.allVarsToSetToolchain()
    # to force covering of cache
    _gottenVars = ToolchainVars.allVarsToSetToolchain()
    assert _gottenVars == gottenVars
    requiredVars = ['CC', 'CXX', 'AS']
    assert sorted(requiredVars) == sorted(gottenVars)

def testVarToSetToolchain():
    LANGMAP = {
        'c'   : 'CC',
        'cxx' : 'CXX',
        'asm' : 'AS',
    }
    for lang in SUPPORTED_LANGS:
        gottenVar = ToolchainVars.varToSetToolchain(lang)
        assert gottenVar == LANGMAP[lang]

    with pytest.raises(ZenMakeError):
        ToolchainVars.varToSetToolchain('')
    with pytest.raises(ZenMakeError):
        ToolchainVars.varToSetToolchain('invalid lang')
