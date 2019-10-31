# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import itertools
import pytest
import tests.common as cmn
from zm.error import ZenMakeError
from zm import toolchains

CompilersInfo = toolchains.CompilersInfo

COMPILERS_MAP = {
    'c'   : {
        'windows': ['msvc', 'gcc', 'clang'],
        'darwin':  ['clang', 'gcc'],
        'linux':   ['gcc', 'clang', 'icc'],
        'default': ['clang', 'gcc'],
    },
    'c++' : {
        'windows': ['msvc', 'g++', 'clang++'],
        'darwin':  ['clang++', 'g++'],
        'linux':   ['g++', 'clang++', 'icpc'],
        'default': ['clang++', 'g++'],
    },
    'asm' : {
        'default':['gas', 'nasm'],
    },
}

SUPPORTED_LANGS = COMPILERS_MAP.keys()

def testAllFlagVars():
    gottenVars = CompilersInfo.allFlagVars()
    # to force covering of cache
    _gottenVars = CompilersInfo.allFlagVars()
    assert _gottenVars == gottenVars
    requiredVars = set([
        'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CFLAGS', 'LINKFLAGS',
        'ASFLAGS',
    ])
    assert requiredVars <= set(gottenVars)

def testAllCfgEnvVars():
    gottenVars = CompilersInfo.allCfgEnvVars()
    # to force covering of cache
    _gottenVars = CompilersInfo.allCfgEnvVars()
    assert _gottenVars == gottenVars
    requiredVars = set([
        'CPPFLAGS', 'CFLAGS', 'LINKFLAGS', 'CXXFLAGS',
        'LDFLAGS', 'DEFINES', 'ASFLAGS',
    ])
    assert requiredVars <= set(gottenVars)

def testAllLangs():
    assert sorted(CompilersInfo.allLangs()) == sorted(SUPPORTED_LANGS)

def testAllVarsToSetCompiler():
    gottenVars = CompilersInfo.allVarsToSetCompiler()
    # to force covering of cache
    _gottenVars = CompilersInfo.allVarsToSetCompiler()
    assert _gottenVars == gottenVars
    requiredVars = ['CC', 'CXX', 'AS']
    assert sorted(requiredVars) == sorted(gottenVars)

def testVarToSetCompiler():
    LANGMAP = {
        'c'   : 'CC',
        'c++' : 'CXX',
        'asm' : 'AS',
    }
    for lang in SUPPORTED_LANGS:
        gottenVar = CompilersInfo.varToSetCompiler(lang)
        assert gottenVar == LANGMAP[lang]

    with pytest.raises(ZenMakeError):
        CompilersInfo.varToSetCompiler('')
    with pytest.raises(ZenMakeError):
        CompilersInfo.varToSetCompiler('invalid lang')

def testCompilers():

    for lang in SUPPORTED_LANGS:
        langCompiler = COMPILERS_MAP[lang]

        for _platform in ('linux', 'windows', 'darwin'):
            compilers = CompilersInfo.compilers(lang, _platform)
            # to force covering of cache
            _compilers = CompilersInfo.compilers(lang, _platform)
            assert _compilers == compilers

            expected = langCompiler.get(_platform, langCompiler['default'])
            assert set(compilers) == set(expected)

        compilers = CompilersInfo.compilers(lang, 'all')
        # to force covering of cache
        _compilers = CompilersInfo.compilers(lang, 'all')
        assert _compilers == compilers
        assert set(compilers) >= \
                        set(itertools.chain(*langCompiler.values()))

    with pytest.raises(ZenMakeError):
        CompilersInfo.compilers('')
    with pytest.raises(ZenMakeError):
        CompilersInfo.compilers('invalid lang')

def testAllCompilers():

    for platform in ('linux', 'windows', 'darwin', 'all'):
        expectedCompilers = []
        for lang in SUPPORTED_LANGS:
            expectedCompilers.extend(CompilersInfo.compilers(lang, platform))
        expectedCompilers = list(set(expectedCompilers))
        assert sorted(CompilersInfo.allCompilers(platform)) == \
                                        sorted(expectedCompilers)
