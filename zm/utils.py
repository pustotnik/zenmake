# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3

if PY3:
    stringtypes = str
else:
    stringtypes = basestring

try:
    from collections.abc import Mapping as maptype
except ImportError:
    from collections import Mapping as maptype

def unfoldPath(cwd, path):
    if not path:
        return path

    if not os.path.isabs(path):
        path = os.path.join(cwd, path)

    path = os.path.expandvars(path)
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    return os.path.normpath(path)

def mksymlink(src, dst, force = True):
    """
    Make symlink, force delete if destination exists already
    """
    if force and (os.path.exists(dst) or os.path.lexists(dst)):
        os.unlink(dst)

    _mksymlink = getattr(os, "symlink", None)
    if callable(_mksymlink):
        _mksymlink(src, dst)
        return
    
    # special case
    # see https://stackoverflow.com/questions/6260149/os-symlink-support-in-windows
    import ctypes
    csl = ctypes.windll.kernel32.CreateSymbolicLinkW
    csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    csl.restype = ctypes.c_ubyte
    flags = 1 if os.path.isdir(src) else 0
    if csl(dst, src, flags) == 0:
        raise ctypes.WinError()

def platform():
    from waflib.Utils import unversioned_sys_platform
    result = unversioned_sys_platform()
    if result.startswith('win32'):
        result = 'windows'
    return result

def loadPyModule(name):
    """
    Load python module by name
    """
    
    # Without non empty fromlist __import__ returns the top-level package
    module = __import__(name, fromlist=[None])
    return module