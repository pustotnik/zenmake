# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import re
from zm import pyutils as _pyutils
from waflib import Utils as wafutils

WINDOWS_RESERVED_FILENAMES = (
    'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
    'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
    'LPT6', 'LPT7', 'LPT8', 'LPT9'
)

def platform():
    """
    Return current system platfom. For MS Windows paltfrom is always 'windows'.
    """
    result = wafutils.unversioned_sys_platform()
    if result.startswith('win32'):
        result = 'windows' # pragma: no cover
    return result

PLATFORM = platform()

readFile           = wafutils.readf
mkHashOfStrings    = wafutils.h_list
normalizeForDefine = wafutils.quote_define_name
Timer              = wafutils.Timer

def normalizeForFileName(s, spaseAsDash = False):
    """
    Convert a string into string suitable for file name
    """
    s = str(s).strip()
    if spaseAsDash:
        s = s.replace(' ', '-')
    else:
        s = s.replace(' ', '_')
    s = re.sub(r'(?u)[^-\w.]', '', s)
    if PLATFORM == 'windows' and s.upper() in WINDOWS_RESERVED_FILENAMES:
        s = '[%s]' % s
    return s

def toList(val):
    """
    Converts a string argument to a list by splitting it by spaces.
    Returns the object if not a string
    """
    if isinstance(val, _pyutils.stringtype):
        return val.split()
    return val

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

    if PLATFORM != 'windows':
        raise NotImplementedError

    # special solution for python 2 on windows
    # see https://stackoverflow.com/questions/6260149/os-symlink-support-in-windows
    import ctypes
    csl = ctypes.windll.kernel32.CreateSymbolicLinkW
    csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    csl.restype = ctypes.c_ubyte
    flags = 1 if os.path.isdir(src) else 0
    if csl(dst, src, flags) == 0:
        raise ctypes.WinError()

def loadPyModule(name, dirpath = None, withImport = True):
    """
    Load python module by name.
    Param 'dirpath' is optional param that is used to add/remove path into sys.path.
    Module is not imported (doesn't exist in sys.modules) if withImport is False.
    With withImport = False you should control where to store returned module object.
    """

    if withImport:
        def doImport(name):
            # Without non empty fromlist __import__ returns the top-level package
            return __import__(name, fromlist=[None])

        if dirpath:
            sys.path.insert(0, dirpath)
            try:
                module = doImport(name)
            finally:
                sys.path.remove(dirpath)
        else:
            module = doImport(name)
        return module

    # In this case we should compile python file manually
    import types
    from zm.error import ZenMakeError
    module = types.ModuleType(name)
    filename = '%s.py' % name.replace('.', os.path.sep)
    if not dirpath:
        # try to find module
        for path in sys.path:
            if os.path.isfile(os.path.join(path, filename)):
                dirpath = path
                break

    if not dirpath:
        raise ImportError('File %r not found' % filename)

    modulePath = os.path.join(dirpath, filename)
    try:
        code = readFile(modulePath, m = 'r', encoding = None)
    except EnvironmentError:
        raise ZenMakeError('Could not read the file %r' % modulePath)

    sys.path.insert(0, dirpath)
    try:
        #pylint: disable=exec-used
        exec(compile(code, modulePath, 'exec'), module.__dict__)
        #pylint: enable=exec-used
    finally:
        sys.path.remove(dirpath)

    module.__file__ = modulePath
    return module

def printSysInfo():
    """
    Print some useful system info. It's for testing mostly.
    """

    import subprocess
    import platform as _platform
    from distutils.spawn import find_executable
    from zm.autodict import AutoDict as _AutoDict

    print('==================================================')
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
        #TODO: find a way to detect msvc
        #_AutoDict(header = 'MSVC:', bin = 'cl', verargs = []),
    ]
    for compiler in compilers:
        _bin = find_executable(compiler.bin)
        if _bin:
            ver = subprocess.check_output([_bin] + compiler.verargs,
                                          universal_newlines = True)
            ver = ver.split('\n')[0]
        else:
            ver = 'not recognized'
        print('%s: %s' % (compiler.header, ver))

    print('==================================================')
