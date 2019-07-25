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

SUPPORTED_LANGS = ('c', 'c++')

class TestToolchains(object):

    def testAllFlagVars(self):
        gottenVars = CompilersInfo.allFlagVars()
        # to force covering of cache
        _gottenVars = CompilersInfo.allFlagVars()
        assert _gottenVars == gottenVars
        requiredVars = ['CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CFLAGS']
        for v in requiredVars:
            assert v in gottenVars

    def testAllCfgEnvVars(self):
        gottenVars = CompilersInfo.allCfgEnvVars()
        # to force covering of cache
        _gottenVars = CompilersInfo.allCfgEnvVars()
        assert _gottenVars == gottenVars
        requiredVars = [
            'CPPFLAGS', 'CFLAGS', 'LINKFLAGS', 'CXXFLAGS',
            'LDFLAGS', 'DEFINES'
        ]
        for v in requiredVars:
            assert v in gottenVars

    def testAllLangs(self):
        assert sorted(CompilersInfo.allLangs()) == sorted(['c', 'c++'])

    def testAllVarsToSetCompiler(self):
        gottenVars = CompilersInfo.allVarsToSetCompiler()
        # to force covering of cache
        _gottenVars = CompilersInfo.allVarsToSetCompiler()
        assert _gottenVars == gottenVars
        requiredVars = ['CC', 'CXX']
        for v in requiredVars:
            assert v in gottenVars

    def testVarToSetCompiler(self):
        LANGMAP = {
            'c'   : 'CC',
            'c++' : 'CXX',
        }
        for lang in SUPPORTED_LANGS:
            gottenVar = CompilersInfo.varToSetCompiler(lang)
            assert gottenVar == LANGMAP[lang]

        with pytest.raises(ZenMakeError):
            CompilersInfo.varToSetCompiler('')
        with pytest.raises(ZenMakeError):
            CompilersInfo.varToSetCompiler('invalid lang')

    def testCompilers(self):
        import importlib

        for lang in SUPPORTED_LANGS:
            wafLang = lang.replace('+', 'x')
            module = importlib.import_module('waflib.Tools.compiler_' + wafLang)
            compilersDict = getattr(module, wafLang + '_compiler')

            for _platform in ('linux', 'windows', 'darwin'):
                wafplatform = _platform
                if _platform == 'windows':
                    wafplatform = 'win32'
                compilers = CompilersInfo.compilers(lang, _platform)
                # to force covering of cache
                _compilers = CompilersInfo.compilers(lang, _platform)
                assert _compilers == compilers
                assert sorted(set(compilers)) == \
                                 sorted(set(compilersDict[wafplatform]))

            compilers = CompilersInfo.compilers(lang, 'all')
            # to force covering of cache
            _compilers = CompilersInfo.compilers(lang, 'all')
            assert _compilers == compilers
            assert sorted(set(compilers)) == \
                            sorted(set(itertools.chain(*compilersDict.values())))

        with pytest.raises(ZenMakeError):
            CompilersInfo.compilers('')
        with pytest.raises(ZenMakeError):
            CompilersInfo.compilers('invalid lang')

    def testAllCompilers(self):

        for platform in ('linux', 'windows', 'darwin', 'all'):
            #wafplatform = _platform
            #if _platform == 'windows':
            #    wafplatform = 'win32'

            expectedCompilers = []
            for lang in SUPPORTED_LANGS:
                expectedCompilers.extend(CompilersInfo.compilers(lang, platform))
            expectedCompilers = list(set(expectedCompilers))
            assert sorted(CompilersInfo.allCompilers(platform)) == \
                                            sorted(expectedCompilers)
