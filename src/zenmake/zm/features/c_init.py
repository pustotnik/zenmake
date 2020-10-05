# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import TASK_TARGET_KINDS
from zm.buildconf.schemeutils import addSelectToParams

VALIDATION_TASKSCHEME_SPEC = {
    'cflags' :    { 'type': ('str', 'list-of-strs') },
    'cppflags' :  { 'type': ('str', 'list-of-strs') },
}
addSelectToParams(VALIDATION_TASKSCHEME_SPEC)

TASK_FEATURES_SETUP = {
    'c' : {
        'target-kinds' : TASK_TARGET_KINDS,
        'file-extensions' : ('.c', '.C',),
    },
}

TOOLCHAIN_VARS = {
    # 'sysenv-var' - environment variable to set compiler
    # 'cfgenv-var' - WAF ConfigSet variable to get/set compiler
    # 'sysenv-flagvars' - env flag variables that have effect from system environment
    # 'cfgenv-flagvars' - WAF ConfigSet variables that are used on 'configure' step
    # and translated from buildconf vars
    'c' : {
        'sysenv-var'      : 'CC',
        'cfgenv-var'      : 'CC',
        'sysenv-flagvars' : ('CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'LINKFLAGS'),
        'cfgenv-flagvars' : ('CFLAGS', 'CPPFLAGS', 'LDFLAGS', 'LINKFLAGS', 'DEFINES'),
    },
}
