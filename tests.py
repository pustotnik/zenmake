#!/usr/bin/env python
# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys 
import os
import unittest
import starter

joinpath = os.path.join

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTS_DIR = joinpath(CURRENT_DIR, 'tests')

def unsetEnviron():
    import zm.toolchains
    varnames = zm.toolchains.CompilersInfo.allVarsToSetCompiler()
    varnames.extend(zm.toolchains.CompilersInfo.allFlagVars())
    for v in varnames:
        os.environ.pop(v, None)

if __name__ == '__main__':
    unsetEnviron()
    suite = unittest.TestLoader().discover(TESTS_DIR)
    unittest.TextTestRunner(verbosity=2).run(suite)