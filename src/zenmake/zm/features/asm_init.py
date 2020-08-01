# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import TASK_TARGET_KINDS, TASK_FEATURE_ALIASES
from zm.buildconf.schemeutils import addSelectToParams

VALIDATION_TASKSCHEME_SPEC = {
    'asflags' : { 'type': ('str', 'list-of-strs') },
    'aslinkflags' : { 'type': ('str', 'list-of-strs') },
}
addSelectToParams(VALIDATION_TASKSCHEME_SPEC)

TASK_FEATURES_SETUP = {
    'asm' : {
        'target-kinds' : TASK_TARGET_KINDS,
        'aliases' : TASK_FEATURE_ALIASES,
        'file-extensions' : ('.s', '.S', '.asm', '.ASM'),
    },
}

TOOLCHAIN_VARS = {
    # 'sysenv-var' - environment variable to set compiler
    # 'cfgenv-var' - WAF ConfigSet variable to get/set compiler
    # 'sysenv-flagvars' - env flag variables that have effect from system environment
    # 'cfgenv-flagvars' - WAF ConfigSet variables that are used on 'configure' step
    # and translated from buildconf vars
    'asm' : {
        'sysenv-var'      : 'AS',
        'cfgenv-var'      : 'AS',
        'sysenv-flagvars' : ('ASFLAGS', 'ASLINKFLAGS', 'LDFLAGS'),
        'cfgenv-flagvars' : ('ASFLAGS', 'ASLINKFLAGS', 'LDFLAGS', 'DEFINES'),
    },
}
