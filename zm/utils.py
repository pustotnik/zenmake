# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3

#pylint: disable=invalid-name,undefined-variable,unused-import

# Some python2/3 compatible stuffs
if PY3:
    stringtypes = str # pragma: no cover
else:
    stringtypes = basestring # pragma: no cover

try:
    from collections.abc import Mapping as maptype
except ImportError:
    from collections import Mapping as maptype

#pylint: enable=invalid-name,undefined-variable,unused-import

def unfoldPath(cwd, path):
    """
    Unfold path applying os.path.expandvars, os.path.expanduser and
    os.path.abspath
    """
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
    """
    Return current system platfom. For MS Windows paltfrom is always 'windows'.
    """
    from waflib.Utils import unversioned_sys_platform
    result = unversioned_sys_platform()
    if result.startswith('win32'):
        result = 'windows' # pragma: no cover
    return result

def loadPyModule(name):
    """
    Load python module by name
    """

    # Without non empty fromlist __import__ returns the top-level package
    module = __import__(name, fromlist=[None])
    return module

def printSysInfo():
    """
    Print some useful system info. It's for testing mostly.
    """

    import subprocess
    import platform as _platform
    from distutils.spawn import find_executable
    from zm.autodict import AutoDict as _AutoDict

    print('= System information =')
    print('CPU name: %s' % _platform.processor())
    print('Bit architecture: %s' % _platform.architecture()[0])
    print('Platform: %s' % platform())
    print('Platform id string: %s' % _platform.platform())
    print('Python version: %s' % _platform.python_version())
    print('Python implementation: %s' % _platform.python_implementation())

    compilers = [
        _AutoDict(header = 'GCC:', bin = 'gcc', verargs = ['--version']),
        _AutoDict(header = 'CLANG:', bin = 'clang', verargs = ['--version']),
        _AutoDict(header = 'MSVC:', bin = 'cl', verargs = []),
    ]
    for compiler in compilers:
        _bin = find_executable(compiler.bin)
        if _bin:
            ver = subprocess.check_output([_bin] + compiler.verargs,
                                          universal_newlines = True)
            ver = ver.split('\n')[0]
        else:
            ver = 'not found'
        print('%s: %s' % (compiler.header, ver))

    print('')
