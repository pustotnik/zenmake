# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

# pylint: disable = unused-import
from waflib.Tools import fc
# pylint: enable = unused-import
from waflib.Tools.compiler_fc import fc_compiler as compilers
from zm import toolchains, conftests

# Fortran compiler g95 is not longer maintained since 2013.
_compilersTable = { p:[x for x in compilers[p] if x != 'g95'] for p in compilers }
toolchains.regToolchains('fc', _compilersTable)

_specificArgs = {
    'code-type': 'fc',
    'compile-filename': 'test.f90',
}

def _checkWrapper(func):

    def execute(checkArgs, params):
        checkArgs.update(_specificArgs)
        func(checkArgs, params)

    return execute

_confTestFuncs = {
    'check-code' : _checkWrapper(conftests.checkCode),
}

conftests.regConfTestFuncs('fc', _confTestFuncs)
