# coding=utf-8
#

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.buildconf.types import PATHS_SCHEME

CONF_TASKSCHEME_SPEC = {
    'base' : {
        'moc' : PATHS_SCHEME,
        'bld-langprefix'   : { 'type': 'str' },
        'unique-qmpaths' : { 'type': 'bool' },
        'rclangprefix'   : { 'type': 'str' },
        'langdir-defname': { 'type': 'str' },
        'install-langdir': { 'type': 'str', 'traits': ['one-path', 'abs'], },
    },
    # Can be boolean or list of particular param names
    # True means all keys from 'base'
    'export' : True,
    # Can be boolean or list of particular param names
    # True means all keys from 'base' and 'export' (prefix 'export-' will be added)
    'select' : True,
}

TASK_FEATURES_SETUP = {
    'qt5' : {}
}
