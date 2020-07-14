# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import signal
import re
import shlex
from copy import deepcopy
from hashlib import sha1
from importlib import import_module as importModule
from types import ModuleType

try:
    import threading
except ImportError:
    raise ImportError('Python must have threading support')

from waflib import Utils as wafutils
from waflib.ConfigSet import ConfigSet
from zm.pyutils import stringtype, _unicode, _encode, PY3
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

def getDefaultDestOS():
    """
    Return value of current platform suitable for Waf env.DEST_OS
    """

    return 'win32' if PLATFORM == 'windows' else PLATFORM

def getDestBinFormatByOS(destOS):
    """
    Return the binary format based on the platform name.
	Returns 'elf' if nothing is found.
    """

    if destOS == 'darwin':
        return 'mac-o'

    if destOS in ('win32', 'cygwin', 'uwin', 'msys', 'windows'):
        return 'pe'

    return 'elf'

def asmethod(cls, methodName = None, wrap = False, callOrigFirst = True):
    """
    Decorator to replace/attach/wrap method to any existing class
    """

    def decorator(func):
        funcName = methodName if methodName else func.__name__
        if wrap:
            origMethod = getattr(cls, funcName)

            if callOrigFirst:
                def execute(*args, **kwargs):
                    retval = origMethod(*args, **kwargs)
                    func(*args, **kwargs)
                    return retval
            else:
                def execute(*args, **kwargs):
                    func(*args, **kwargs)
                    return origMethod(*args, **kwargs)

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
subprocess         = wafutils.subprocess

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
    Return new list with preserved the original order of the list.
    Each element in lst must be hashable.
    """

    used = set()
    return [x for x in lst if x not in used and (used.add(x) or True)]

def uniqueDictListWithOrder(lst):
    """
    Return new list with preserved the original order of the list.
    It works only with list of dicts.
    """

    used = set()
    result = []
    for elem in lst:
        key = frozenset(elem.items())
        if key in used:
            continue
        result.append(elem)
        used.add(key)

    return result

def envValToBool(rawVal):
    """
    Return env val as native bool value.
    Returns False if not recognized.
    """

    result = False
    if rawVal:
        try:
            # value from os.environ is a string but it may be a digit
            result = bool(int(rawVal))
        except ValueError:
            result = rawVal in ('true', 'True', 'yes')

    return result

def cmdHasShellSymbols(cmdline):
    """
    Return True if string 'cmdline' contains some specific shell symbols
    """
    return any(s in cmdline for s in ('<', '>', '&&', '||'))

def copyEnv(env):
    """
    Make shallow copy of ConfigSet object
    """

    newenv = ConfigSet()
    # copy only current table whithout parents
    newenv.table = env.table.copy()
    parent = getattr(env, 'parent', None)
    if parent is not None:
        newenv.parent = parent
    return newenv

def deepcopyEnv(env, filterKeys = None):
    """
    Make deep copy of ConfigSet object

    Function deepcopy doesn't work with ConfigSet and ConfigSet.detach
    doesn't make deepcopy for already detached objects.
    """

    # keys() returns all keys from current env and all parents
    keys = env.keys()
    if filterKeys is not None:
        keys = [ x for x in keys if filterKeys(x) ]

    newenv = ConfigSet()
    newenv.table = { k:deepcopy(env[k]) for k in keys }
    return newenv

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
    if force and os.path.lexists(dst):
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

class ProcCmd(object):
    """
    Class to run external command in a subprocess
    """

    def __init__(self, cmdLine, shell = False, stdErrToOut = True):

        self._origCmdLine = cmdLine

        cmdAsStr = isinstance(cmdLine, stringtype)
        if PLATFORM == 'windows':
            # On Windows, if args is a sequence, it will be converted to a
            # string in 'subprocess' module regardless of 'shell' value.
            # So on Windows cmdLine can be used as a string in any case.
            if not shell:
                shell = cmdHasShellSymbols(cmdLine)
        else:
            if shell and not cmdAsStr:
                cmdLine = ' '.join(cmdLine)
            elif not shell and cmdAsStr:
                shell = cmdHasShellSymbols(cmdLine)
                if not shell:
                    cmdLine = shlex.split(cmdLine)

        self._cmdLine = cmdLine
        self._proc = None
        self._timeoutExpired = False
        self._popenArgs = {
            'shell' : shell,
            'stdout' : subprocess.PIPE,
            'stderr' : subprocess.PIPE,
            'universal_newlines' : True,
        }

        if stdErrToOut:
            self._popenArgs['stderr'] = subprocess.STDOUT

        if PY3:
            # start_new_session was added in python 3.2
            # Use 'start_new_session' to change the process(forked) group id to itself
            # so os.killpg with proc.pid can be used.
            # This parameter does nothing on Windows.
            self._popenArgs['start_new_session'] = True

    def _communicate(self):
        stdout, stderr = self._proc.communicate()
        return self._proc.returncode, stdout, stderr

    def _communicateCallback(self, callback):
        proc = self._proc
        while True:
            noData = True
            if proc.stdout:
                line = proc.stdout.readline()
                if line:
                    noData = False
                    callback(line, err = False)
            if proc.stderr:
                line = proc.stderr.readline()
                if line:
                    noData = False
                    callback(line, err = True)
            if noData and proc.poll() is not None:
                break

        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()
        return proc.returncode

    def run(self, cwd = None, env = None, timeout = None, outCallback = None):
        """
        Run command.
        Parameter outCallback can be used to handle stdout/stderr line by line
        without waiting for a process to exit.
        Returns tuple (exitcode, stdout, stderr) or exitcode if outCallback is not None.
        """

        kwargs = self._popenArgs
        kwargs.update({
            'cwd' : cwd,
            'env' : env,
        })

        self._proc = subprocess.Popen(self._cmdLine, **kwargs)

        timer = None
        if timeout is not None:
            self._timeoutExpired = False

            def killProc(self):
                proc = self._proc
                if kwargs.get('start_new_session') and hasattr(os, 'killpg'):
                    # If 'shell' is true then killing of current process is killing of
                    # executed shell but not childs.
                    # Unix only.
                    os.killpg(proc.pid, signal.SIGKILL)
                else:
                    proc.kill()
                self._timeoutExpired = True

            timer = threading.Timer(timeout, killProc, args = [self])
            # allow entire program to exit on unexpected exception like KeyboardInterrupt
            timer.daemon = True
            timer.start()

        if outCallback is None:
            result = self._communicate()
        else:
            result = self._communicateCallback(outCallback)

        if self._timeoutExpired:
            stdout = ''
            if outCallback is None:
                stdout = result[1]
            raise ZenMakeProcessTimeoutExpired(self._origCmdLine, timeout, stdout)

        if timer:
            timer.cancel()

        # release Popen object
        self._proc = None
        return result

def runCmd(cmdLine, cwd = None, env = None, shell = False,
           timeout = None, stdErrToOut = True, outCallback = None):
    """
    Run external command in a subprocess.
    Parameter outCallback can be used to handle stdout/stderr line by line
    without waiting for a process to exit.
    Returns tuple (exitcode, stdout, stderr) or exitcode if outCallback is not None.
    """

    # pylint: disable = too-many-arguments

    procCmd = ProcCmd(cmdLine, shell, stdErrToOut)
    return procCmd.run(cwd, env, timeout, outCallback)
