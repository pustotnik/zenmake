# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import TASK_TARGET_KINDS, TASK_FEATURE_ALIESES
from zm.buildconf.schemeutils import addSelectToParams

VALIDATION_TASKSCHEME_SPEC = {
    'fcflags' :  { 'type': ('str', 'list-of-strs') },
}
addSelectToParams(VALIDATION_TASKSCHEME_SPEC)

TASK_FEATURES_SETUP = {
    'fc' : {
        'target-kinds' : TASK_TARGET_KINDS,
        'alieses' : TASK_FEATURE_ALIESES,
        'file-extensions' : (
            '.f', '.F', '.f90', '.F90', '.for', '.FOR',
            '.f95', '.F95', '.f03', '.F03', '.f08', '.F08',
        ),
    },
}

TOOLCHAIN_VARS = {
    # 'sysenv-var' - environment variable to set compiler
    # 'cfgenv-var' - WAF ConfigSet variable to get/set compiler
    # 'sysenv-flagvars' - env flag variables that have effect from system environment
    # 'cfgenv-flagvars' - WAF ConfigSet variables that are used on 'configure' step
    # and translated from buildconf vars
    'fc' : {
        'sysenv-var'      : 'FC',
        'cfgenv-var'      : 'FC',
        'sysenv-flagvars' : ('FCFLAGS', 'LINKFLAGS', 'LDFLAGS',),
        'cfgenv-flagvars' : ('FCFLAGS', 'LINKFLAGS', 'LDFLAGS', 'DEFINES', ),
    },
}
