# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

CONF_TASKSCHEME_SPEC = {
    'base' : {
        'arflags' :    { 'type': ('str', 'list-of-strs') },
    },
    # Can be boolean or list of particular param names
    # True means all keys from 'base' and 'export' (prefix 'export-' will be added)
    'select' : True,
}

TOOLCHAIN_VARS = {
    # 'sysenv-var' - environment variable to set tool
    # 'cfgenv-var' - WAF ConfigSet variable to get/set tool
    # 'sysenv-flagvars' - env flag variables that have effect from system environment
    # 'cfgenv-flagvars' - WAF ConfigSet variables that are used on 'configure' step
    # and translated from buildconf vars
    'ar' : {
        'sysenv-var'      : 'AR',
        'cfgenv-var'      : 'AR',
        'sysenv-flagvars' : ('ARFLAGS',),
        'cfgenv-flagvars' : ('ARFLAGS',),
    },
}
