# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import re
import shlex
from hashlib import sha1
from importlib import import_module as importModule
from types import ModuleType

from waflib import Utils as wafutils
from zm.pyutils import stringtype, _unicode, _encode
from zm.error import ZenMakeError, ZenMakeProcessTimeoutExpired

_joinpath = os.path.join

WINDOWS_RESERVED_FILENAMES = frozenset((
    'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
    'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
    'LPT6', 'LPT7', 'LPT8', 'LPT9'
))

_RE_UNSAFE_FILENAME_CHARS = re.compile(r'[^-\w.]', re.UNICODE)
_RE_TOLIST = re.compile(r"""((?:[^\s"']|"[^"]*"|'[^']*')+)""")

def platform():
    """
    Return current system platform. For MS Windows platform is always 'windows'.
    """
    result = wafutils.unversioned_sys_platform()
    if result.startswith('win32'):
        result = 'windows' # pragma: no cover
    return result

PLATFORM = platform()

def asmethod(cls, methodName = None, wrap = False, callOrigFirst = True):
    """
    Decorator to replace/attach method to any existing class
    """

    def decorator(func):
        funcName = methodName if methodName else func.__name__
        if wrap:
            origMethod = getattr(cls, funcName)

            if callOrigFirst:
                def execute(*args, **kwargs):
                    origMethod(*args, **kwargs)
                    func(*args, **kwargs)
            else:
                def execute(*args, **kwargs):
                    func(*args, **kwargs)
                    origMethod(*args, **kwargs)

            setattr(cls, funcName, execute)
        else:
            setattr(cls, funcName, func)
        return func

    return decorator

md5                = wafutils.md5
HashAlgo           = sha1
readFile           = wafutils.readf
hashObj            = wafutils.h_list
hashFunc           = wafutils.h_fun
hexOfStr           = wafutils.to_hex
substVars          = wafutils.subst_vars
libDirPostfix      = wafutils.lib64
Timer              = wafutils.Timer
threading          = wafutils.threading
subprocess         = wafutils.subprocess

try:
    TimeoutExpired = subprocess.TimeoutExpired
    PROCESS_TIMEOUT_SUPPORTED = True
except AttributeError:
    class TimeoutExpired(Exception):
        """ Emulation of TimeoutExpired """

    PROCESS_TIMEOUT_SUPPORTED = False

def setDefaultHashAlgo(algo):
    """
    Set default hash algo. Can be 'sha1' or 'md5'.
    """

    # pylint: disable = global-statement
    global HashAlgo
    if algo == 'md5':
        HashAlgo = wafutils.md5 = md5
    else:
        HashAlgo = wafutils.md5 = sha1

# Since python 3.4 non-inheritable file handles are provided by default
if hasattr(os, 'O_NOINHERIT') and sys.hexversion < 0x3040000:
    def _hashFile(hashobj, path):
        # pylint: disable = no-member
        try:
            fd = os.open(path, os.O_BINARY | os.O_RDONLY | os.O_NOINHERIT)
        except OSError:
            raise OSError('Cannot read from %r' % path)

        with os.fdopen(fd, 'rb') as file:
            result = True
            while result:
                result = file.read(200000)
                hashobj.update(result)
        return hashobj
else:
    def _hashFile(hashobj, path):

        with open(path, 'rb') as file:
            result = True
            while result:
                result = file.read(200000)
                hashobj.update(result)
        return hashobj

def hashFile(path):
    """ Hash file by using sha1/md5 """
    _hash = HashAlgo()
    return _hashFile(_hash, path).digest()

def hashFiles(paths):
    """
    Hash files from paths by using sha1/md5.
    Order of paths must be constant. Simple way to do it is to sort the path items.
    """

    # Old implementation (slower and less accurate):
    #_hash = 0
    #for path in paths:
    #    _hash = hashObj((_hash, readFile(path, 'rb')))
    #return _hash

    _hash = HashAlgo()
    for path in paths:
        _hashFile(_hash, path)
    return _hash.digest()

def normalizeForDefine(s):
    """
	Converts a string into an identifier suitable for C defines.
    """
    if s[0].isdigit():
        s = '_%s' % s
    return wafutils.quote_define_name(s)

def normalizeForFileName(s, spaceAsDash = False):
    """
    Convert a string into string suitable for file name
    """
    s = _unicode(s).strip()
    if spaceAsDash:
        s = s.replace(' ', '-')
    else:
        s = s.replace(' ', '_')
    s = _encode(_RE_UNSAFE_FILENAME_CHARS.sub('', s))
    if PLATFORM == 'windows' and s.upper() in WINDOWS_RESERVED_FILENAMES:
        s = '_%s' % s
    return s

def stripQuotes(val):
    """
    Strip quotes ' or " from the begin and the end of a string but do it only
    if they are the same on both sides.
    """

    if not val:
        return val

    if len(val) < 2:
        return val

    first = val[0]
    last = val[-1]
    if first == last and first in ("'", '"'):
        return val[1:-1]

    return val

def toListSimple(val):
    """
    Converts a string argument to a list by splitting it by spaces.
    Returns the object if not a string
    """
    if not isinstance(val, stringtype):
        return val
    return val.split()

def toList(val):
    """
    Converts a string argument to a list by splitting it by spaces.
    This version supports preserving quoted substrings with spaces by works
    slower than toListSimple does.
    Returns the object if not a string
    """
    if not isinstance(val, stringtype):
        return val

    if not ('"' in val or "'" in val): # optimization
        return val.split()

    # shlex.split worked quite well but did it too slowly

    # It can be made without regexp but this solution works faster.
    # Actually manual function should be faster but python regexp engine uses
    # some C code and therefore it works faster.
    return [stripQuotes(x) for x in _RE_TOLIST.split(val)[1::2]]

def uniqueListWithOrder(lst):
    """
    Return new list with preserved the original order of the list
    """
    used = set()
    return [x for x in lst if x not in used and (used.add(x) or True)]

def cmdHasShellSymbols(cmdline):
    """
    Return True if string 'cmdline' contains some specific shell symbols
    """
    return any(s in cmdline for s in ('<', '>', '&&', '||'))

def configSetToDict(configSet):
    """
    Convert Waf ConfigSet to python dict
    """
    result = configSet.get_merged_dict()
    result.pop('undo_stack', None)
    return result

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

def printInWorkStatus(title = '', end = False):
    """
    Print 'in work' status like emerge does it.
    """

    statusSymbols = ('\\', '|', '/', '-',)

    try:
        printInWorkStatus.index += 1
        if printInWorkStatus.index >= len(statusSymbols):
            printInWorkStatus.index = 0
    except AttributeError:
        printInWorkStatus.index = 0

    symbols = '' if end else title + ' ' + statusSymbols[printInWorkStatus.index]
    sys.stdout.write("\r" + symbols)
    sys.stdout.flush()

def _loadPyModuleWithoutImport(name):

    # In this case we should compile python file manually
    # WARN: It has no support for all python module attributes.

    from zm.pypkg import PkgPath

    module = ModuleType(name)
    filename = name.replace('.', os.path.sep)

    # try to find module
    isPkg = False
    for path in sys.path:
        modulePath = _joinpath(path, filename)
        path = PkgPath(modulePath + '.py')
        if path.isfile():
            modulePath = path
            break
        path = PkgPath(_joinpath(modulePath, '__init__.py'))
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

    # pylint: disable = exec-used
    exec(compile(code, modulePath.path, 'exec'), module.__dict__)

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
        loadModule = importModule
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

def runExternalCmd(cmdLine, cwd = None, env = None, shell = False, timeout = None):
    """
    Run external command in a subprocess.
    Returns tuple (exitcode, stdout, stderr).
    """

    origCmdLine = cmdLine
    cmdAsStr = isinstance(cmdLine, stringtype)
    if shell and not cmdAsStr:
        cmdLine = ' '.join(cmdLine)
    elif not shell and cmdAsStr:
        shell = cmdHasShellSymbols(cmdLine)
        if not shell:
            cmdLine = shlex.split(cmdLine)

    kwargs = {
        'cwd' : cwd,
        'shell' : shell,
        'stdout' : subprocess.PIPE,
        'stderr' : subprocess.STDOUT,
        'env' : env,
        'universal_newlines' : True,
    }

    ckwargs = {}

    if PROCESS_TIMEOUT_SUPPORTED:
        ckwargs['timeout'] = timeout

    proc = subprocess.Popen(cmdLine, **kwargs)

    try:
        stdout, stderr = proc.communicate(**ckwargs)
    except TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        raise ZenMakeProcessTimeoutExpired(origCmdLine, timeout, stdout)

    return proc.returncode, stdout, stderr
