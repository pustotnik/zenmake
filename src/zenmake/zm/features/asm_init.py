# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import TASK_TARGET_KINDS, TASK_FEATURE_ALIESES

VALIDATION_TASKSCHEME_SPEC = {
    'asflags' : { 'type': ('str', 'list-of-strs') },
    'aslinkflags' : { 'type': ('str', 'list-of-strs') },
}

TASK_FEATURES_SETUP = {
    'asm' : {
        'target-kinds' : TASK_TARGET_KINDS,
        'alieses' : TASK_FEATURE_ALIESES,
        'file-extensions' : ('.s', '.S', '.asm', '.ASM'),
    },
}

TOOLCHAIN_VARS = {
    # 'env-var' - environment variable to set compiler
    # 'env-flagvars' - env flag variables that have effect from system environment
    # 'cfgenv-vars' - WAF ConfigSet variables that are used on 'configure' step
    'asm' : {
        'env-var'      : 'AS',
        'env-flagvars' : ('ASFLAGS', 'ASLINKFLAGS', 'LDFLAGS'),
        'cfgenv-vars'  : ('ASFLAGS', 'ASLINK', 'ASLINKFLAGS', 'DEFINES'),
    },
}
