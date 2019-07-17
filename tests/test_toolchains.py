# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import pytest
import tests.common as cmn
from waflib import Utils
from waflib.Errors import WafError
from zm import toolchains

CompilersInfo = toolchains.CompilersInfo

SUPPORTED_LANGS = ('c', 'c++')

class TestToolchains(object):

    def testAllFlagVars(self):
        gottenVars = CompilersInfo.allFlagVars()
        requiredVars = ['CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CFLAGS']
        for v in requiredVars:
            assert v in gottenVars

    def testAllCfgEnvVars(self):
        gottenVars = CompilersInfo.allCfgEnvVars()
        requiredVars = [
            'CPPFLAGS', 'CFLAGS', 'LINKFLAGS', 'CXXFLAGS',
            'LDFLAGS', 'DEFINES'
        ]
        for v in requiredVars:
            assert v in gottenVars

    def testAllVarsToSetCompiler(self):
        gottenVars = CompilersInfo.allVarsToSetCompiler()
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

        with pytest.raises(WafError):
            CompilersInfo.varToSetCompiler('')
        with pytest.raises(WafError):
            CompilersInfo.varToSetCompiler('invalid lang')

    def testCompilers(self):
        import importlib

        # We must use Waf function here
        platform = Utils.unversioned_sys_platform()

        for lang in SUPPORTED_LANGS:
            wafLang = lang.replace('+', 'x')
            module = importlib.import_module('waflib.Tools.compiler_' + wafLang)
            compilersDict = getattr(module, wafLang + '_compiler')

            assert list(set(CompilersInfo.compilers(lang))) == \
                                 list(set(compilersDict[platform]))

        with pytest.raises(WafError):
            CompilersInfo.compilers('')
        with pytest.raises(WafError):
            CompilersInfo.compilers('invalid lang')
