# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.buildconf.schemeutils import addSelectToParams

VALIDATION_TASKSCHEME_SPEC = {
    'libs' :        { 'type': ('str', 'list-of-strs') },
    'libpath':      { 'type': ('str', 'list-of-strs') },
    'stlibs' :      { 'type': ('str', 'list-of-strs') },
    'stlibpath':    { 'type': ('str', 'list-of-strs') },
    'rpath' :       { 'type': ('str', 'list-of-strs') },
    'ver-num' :     { 'type': 'str' },
    'includes':     { 'type': ('str', 'list-of-strs') },
    'linkflags' :   { 'type': ('str', 'list-of-strs') },
    'ldflags' :     { 'type': ('str', 'list-of-strs') },
    'defines' :     { 'type': ('str', 'list-of-strs') },
    'export-includes' : { 'type': ('bool', 'str', 'list-of-strs') },
    'export-defines' :  { 'type': ('bool', 'str', 'list-of-strs') },
}
addSelectToParams(VALIDATION_TASKSCHEME_SPEC)

def getBuildConfTaskParamHooks():
    """
    Get pairs of (param, function) where the function is called during
    processing of task param in buildconf before actual processing
    """

    def handleParam(bconf, param):
        if param is None:
            return None

        # apply startdir
        return dict(startdir = bconf.startdir, paths = param)

    paramNames = ('includes', 'export-includes', 'libpath')
    return [(x, handleParam) for x in paramNames]
