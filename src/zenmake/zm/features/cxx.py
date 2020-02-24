# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Tools.c_config import SNIP_EMPTY_PROGRAM as EMPTY_PROGRAM
from waflib.Tools.compiler_cxx import cxx_compiler
from zm import toolchains, conftests

toolchains.regToolchains('cxx', cxx_compiler)

_specificArgs = {
    'code-type': 'cxx',
    'compile-filename': 'test.cpp',
    'code' : EMPTY_PROGRAM,
}

def _checkWrapper(funcName):

    func = getattr(conftests, funcName)

    def execute(checkArgs, params):
        checkArgs.update(_specificArgs)
        func(checkArgs, params)

    return execute

_confTestFuncs = {
    'check-sys-libs'      : _checkWrapper('checkSysLibs'),
    'check-headers'       : _checkWrapper('checkHeaders'),
    'check-libs'          : _checkWrapper('checkLibs'),
    'check-code'          : _checkWrapper('checkCode'),
    'write-config-header' : conftests.writeConfigHeader,
}

conftests.regConfTestFuncs('cxx', _confTestFuncs)
