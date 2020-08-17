# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Tools.c_config import SNIP_EMPTY_PROGRAM as EMPTY_PROGRAM
from waflib.Tools.compiler_c import c_compiler as compilers
from zm import toolchains
from zm.waf import config_actions as configActions

toolchains.regToolchains('c', compilers)

_specificArgs = {
    'code-type': 'c',
    'compile-filename': 'test.c',
    'code' : EMPTY_PROGRAM,
}

def _checkWrapper(func):

    def execute(checkArgs, params):
        checkArgs.update(_specificArgs)
        func(checkArgs, params)

    return execute

_confActionFuncs = {
    'check-headers'       : _checkWrapper(configActions.checkHeaders),
    'check-libs'          : _checkWrapper(configActions.checkLibs),
    'check-code'          : _checkWrapper(configActions.checkCode),
    'pkgconfig'           : configActions.doPkgConfig,
    'write-config-header' : configActions.writeConfigHeader,
}

configActions.regActionFuncs('c', _confActionFuncs)
