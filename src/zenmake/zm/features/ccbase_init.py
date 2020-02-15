# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

VALIDATION_TASKSCHEME_SPEC = {
    'sys-libs' :    { 'type': ('str', 'list-of-strs') },
    'libpath':      { 'type': ('str', 'list-of-strs') },
    'rpath' :       { 'type': ('str', 'list-of-strs') },
    'ver-num' :     { 'type': 'str' },
    'includes':     { 'type': ('str', 'list-of-strs') },
    'linkflags' :   { 'type': ('str', 'list-of-strs') },
    'ldflags' :     { 'type': ('str', 'list-of-strs') },
    'defines' :     { 'type': ('str', 'list-of-strs') },
    'export-includes' : { 'type': ('bool', 'str', 'list-of-strs') },
    'export-defines' :  { 'type': ('bool', 'str', 'list-of-strs') },
    'object-file-counter' : { 'type': 'int' },
}
