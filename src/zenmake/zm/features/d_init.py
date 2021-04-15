# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import TASK_TARGET_KINDS

CONF_TASKSCHEME_SPEC = {
    'base' : {
        'dflags' :  { 'type': ('str', 'list-of-strs') },
    },
    # Can be boolean or list of particular param names
    # True means all keys from 'base' and 'export' (prefix 'export-' will be added)
    'select' : True,
}

TASK_FEATURES_SETUP = {
    'd' : {
        'target-kinds' : TASK_TARGET_KINDS,
        'file-extensions' : ('.d', '.D', '.di', '.DI'),
    },
}

TOOLCHAIN_VARS = {
    # 'sysenv-var' - environment variable to set compiler
    # 'cfgenv-var' - WAF ConfigSet variable to get/set compiler
    # 'sysenv-flagvars' - env flag variables that have effect from system environment
    # 'cfgenv-flagvars' - WAF ConfigSet variables that are used on 'configure' step
    # and translated from buildconf vars
    'd' : {
        'sysenv-var'      : 'DC',
        'cfgenv-var'      : 'D',
        'sysenv-flagvars' : ('DFLAGS', 'LINKFLAGS', 'LDFLAGS',),
        'cfgenv-flagvars' : ('DFLAGS', 'LINKFLAGS', 'LDFLAGS',),
    },
}
