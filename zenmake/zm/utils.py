# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import importlib
import re

from waflib import Utils as wafutils
from zm import pyutils as _pyutils
from zm.pypkg import PkgPath

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
        s = '_%s' % s
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

    raise NotImplementedError

def _loadPyModuleWithoutImport(name):

    # In this case we should compile python file manually
    # WARN: It has no support for all python module attributes.

    import types
    from zm.error import ZenMakeError
    joinpath = os.path.join

    module = types.ModuleType(name)
    filename = name.replace('.', os.path.sep)

    # try to find module
    isPkg = False
    for path in sys.path:
        modulePath = joinpath(path, filename)
        path = PkgPath(modulePath + '.py')
        if path.isfile():
            modulePath = path
            break
        path = PkgPath(joinpath(modulePath, '__init__.py'))
        if path.isfile():
            modulePath = path
            isPkg = True
            break
    else:
        raise ImportError('File %r not found' % filename)

    try:
        code = modulePath.read()
    except EnvironmentError:
        raise ZenMakeError('Could not read the file %r' % str(modulePath))

    module.__file__ = modulePath.path

    #pylint: disable=exec-used
    exec(compile(code, modulePath.path, 'exec'), module.__dict__)
    #pylint: enable=exec-used

    # From https://docs.python.org/3/reference/import.html:
    #
    # The module’s __package__ attribute should be set. Its value must be
    # a string, but it can be the same value as its __name__. If the attribute
    # is set to None or is missing, the import system will fill it in with
    # a more appropriate value. When the module is a package, its __package__
    # value should be set to its __name__. When the module is not a package,
    # __package__ should be set to the empty string for top-level modules, or
    # for submodules, to the parent package’s name.
    if isPkg:
        module.__package__ = name
    else:
        lastdotpos = name.rfind('.')
        module.__package__ = '' if lastdotpos < 0 else name[0:lastdotpos]
    return module

def loadPyModule(name, dirpath = None, withImport = True):
    """
    Load python module by name.
    Param 'dirpath' is optional param that is used to add/remove path into sys.path.
    Module is not imported (doesn't exist in sys.modules) if withImport is False.
    With withImport = False you should control where to store returned module object.
    """

    if withImport:
        loadModule = importlib.import_module
    else:
        loadModule = _loadPyModuleWithoutImport

    if dirpath:
        sys.path.insert(0, dirpath)
        try:
            module = loadModule(name)
        finally:
            sys.path.pop(0)
    else:
        module = loadModule(name)
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
