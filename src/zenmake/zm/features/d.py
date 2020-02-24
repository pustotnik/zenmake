# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm import toolchains, conftests

toolchains.regToolchains('d', { 'default': ('ldc2', 'gdc', 'dmd'), })

_specificArgs = {
    'code-type': 'd',
    'compile-filename': 'test.d',
}

def _checkWrapper(func):

    def execute(checkArgs, params):
        checkArgs.update(_specificArgs)
        func(checkArgs, params)

    return execute

_confTestFuncs = {
    'check-code' : _checkWrapper(conftests.checkCode),
}

conftests.regConfTestFuncs('d', _confTestFuncs)
