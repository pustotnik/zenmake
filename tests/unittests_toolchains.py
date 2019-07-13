# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import unittest
import tests.common as cmn
from waflib import Utils
from waflib.Errors import WafError
import zm.toolchains

CompilersInfo = zm.toolchains.CompilersInfo

SUPPORTED_LANGS = ('c', 'c++')

class TestToolchains(unittest.TestCase):

    def setUp(self):
        self.longMessage = True

    def tearDown(self):
        pass

    def testAllFlagVars(self):
        gottenVars = CompilersInfo.allFlagVars()
        requiredVars = ['CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'CFLAGS']
        for v in requiredVars:
            self.assertIn(v, gottenVars)

    def testAllCfgEnvVars(self):
        gottenVars = CompilersInfo.allCfgEnvVars()
        requiredVars = [
            'CPPFLAGS', 'CFLAGS', 'LINKFLAGS', 'CXXFLAGS',
            'LDFLAGS', 'DEFINES'
        ]
        for v in requiredVars:
            self.assertIn(v, gottenVars)

    def testAllVarsToSetCompiler(self):
        gottenVars = CompilersInfo.allVarsToSetCompiler()
        requiredVars = ['CC', 'CXX']
        for v in requiredVars:
            self.assertIn(v, gottenVars)

    def testVarToSetCompiler(self):
        LANGMAP = {
            'c'   : 'CC',
            'c++' : 'CXX',
        }
        for lang in SUPPORTED_LANGS:
            gottenVar = CompilersInfo.varToSetCompiler(lang)
            self.assertEqual(gottenVar, LANGMAP[lang])

        with self.assertRaises(WafError):
            CompilersInfo.varToSetCompiler('')
        with self.assertRaises(WafError):
            CompilersInfo.varToSetCompiler('invalid lang')

    def testCompilers(self):
        import importlib

        # We must use Waf function here
        platform = Utils.unversioned_sys_platform()

        for lang in SUPPORTED_LANGS:
            wafLang = lang.replace('+', 'x')
            module = importlib.import_module('waflib.Tools.compiler_' + wafLang)
            compilersDict = getattr(module, wafLang + '_compiler')
            self.assertListEqual(
                                 list(set(CompilersInfo.compilers(lang))),
                                 list(set(compilersDict[platform])))

        with self.assertRaises(WafError):
            CompilersInfo.compilers('')
        with self.assertRaises(WafError):
            CompilersInfo.compilers('invalid lang')
