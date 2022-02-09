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
import inspect
import platform as _platform
from copy import deepcopy
from hashlib import sha1
from importlib import import_module as importModule
from types import ModuleType

try:
    import threading
except ImportError as _pex:
    raise ImportError('Python must have threading support') from _pex

from waflib import Utils as wafutils
from waflib.ConfigSet import ConfigSet
from zm.pyutils import stringtype, maptype, struct, _unicode, _encode
from zm.error import ZenMakeError, ZenMakeProcessTimeoutExpired
from zm.buildconf.types import ConfNode

_joinpath = os.path.join

WINDOWS_RESERVED_FILENAMES = frozenset((
    'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
    'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
    'LPT6', 'LPT7', 'LPT8', 'LPT9'
))

_USABLE_WHITESPACE = ' \t\n\r\v'

_RE_UNSAFE_FILENAME_CHARS = re.compile(r'[^-\w.]', re.UNICODE)
_RE_TOLIST = re.compile(r"""((?:[^\s"']|"[^"]*"|'[^']*')+)""", re.ASCII)
_RE_SUBST_VARS = re.compile(r"\${1,2}(\w+)|\${1,2}\{\s*(\w+)\s*\}", re.ASCII)
_RE_SUBST_BUILTINVARS = re.compile(r"\$\((\s*(\w+)\s*)\)", re.ASCII)

def platform():
    """
    Return current system platform. It is always 'windows' for MS Windows.
    """
    result = wafutils.unversioned_sys_platform()
    if result.startswith('win32'):
        result = 'windows' # pragma: no cover
    return result

PLATFORM = platform()

def hostOS():
    """
    Return current host operating system base name.
    It is 'windows' for MS Windows, MSYS2 and cygwin;
    'linux' for GNU/Linux; 'macos' for Mac OS, etc.
    """

    selector = {
        'cygwin' : 'windows',
        'msys'   : 'windows',
        'darwin' : 'macos',
    }

    return selector.get(PLATFORM, PLATFORM)

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

def distroInfo():
    """
    Return dict of info from /etc/os-release or /usr/lib/os-release.
    Returns {} if failed
    """

    result = {}

    filePath = "/etc/os-release"
    if not os.path.isfile(filePath):
        filePath = "/usr/lib/os-release"
    if not os.path.isfile(filePath):
        return result

    import csv
    try:
        with open(filePath) as file:
            reader = csv.reader(file, delimiter = "=")
            result = { row[0]:row[1] for row in reader if row}
    except OSError:
        pass

    return result

def toPosixArchName(name):
    """
    Get 'standard' POSIX names for machine architecture type.
    It means that for 'amd64' it returns 'x86_64', etc.
    """

    name = name.lower()
    namesMap = {
        'x86_64' : 'x86_64',
        'amd64'  : 'x86_64',
        'i386'   : 'i386',
        'x86'    : 'i386',
    }

    return namesMap.get(name, name)

def unixLibDirPostfix():
    """
    Return postfix of lib dirs on UNIX
    """

    isdir = os.path.isdir

    # Debian, Ubuntu, etc
    isDebianLike = PLATFORM == 'linux' and os.path.isfile('/etc/debian_version')
    if isDebianLike:
        # at first try to detect without call dpkg-architecture
        pattern = '%s-linux-gnu'
        hostArch = _platform.machine().lower()

        params = [
            (('x86_64', 'amd64'), 'x86_64'),
            (('i386', 'i586', 'i686'), 'i386'),
        ]
        for variants,  arch in params:
            dirname = pattern % arch
            if hostArch in variants and isdir('/usr/lib/' + dirname):
                return '/%s' % dirname

        try:
            result = runCmd(['dpkg-architecture', '-qDEB_HOST_MULTIARCH'],
                            captureOutput = True)
            if result.exitcode == 0:
                return '/%s' % result.stdout.strip()
        except ZenMakeError:
            pass

    if PLATFORM in ('freebsd', 'irix'):
        return ''

    if os.sep == '/' and _platform.architecture()[0] == '64bit' and \
        isdir('/usr/lib64') and \
        not os.path.exists('/usr/lib32'):

        return '64'

    return ''

md5                = wafutils.md5
readFile           = wafutils.readf
hashOrdObj         = wafutils.h_list
hexOfStr           = wafutils.to_hex
Timer              = wafutils.Timer
subprocess         = wafutils.subprocess

def mayHaveSubstVar(strval):
    """
    Return True if the strval MAY have substitution variable.
    Return False if the strval has no substitution variable.
    """
    return '$' in strval

def substVars(strval, svarGetter, envVars = None, foundEnvVars = None):
    """
	Return string with $VAR/${VAR} replaced by the value of VAR taken by svarGetter
    """

    if not mayHaveSubstVar(strval): # optimization
        return strval

    if envVars is None:
        envVars = {}

    def replaceVar(match):
        foundName = match.group(1,2)
        foundName = [x for x in foundName if x][0]

        origName = match.group(0)
        foundVal = None
        useEnv = origName[:2] != '$$'
        if useEnv:
            foundVal = envVars.get(foundName)
            if foundEnvVars is not None:
                foundEnvVars.add(foundName)

        if foundVal is None:
            foundVal = svarGetter(foundName)

        if foundVal is None:
            # leave it for Waf if it doesn't start with $$
            foundVal = "${%s}" % foundName if useEnv else ""

        return foundVal

    return _RE_SUBST_VARS.sub(replaceVar, strval)

def substBuiltInVars(strval, svars, check = True, notHandled = None):
    """
	Return string with $(VAR) replaced by the value of VAR taken from a dict
    """

    if check and not mayHaveSubstVar(strval): # optimization
        return strval

    def replaceVar(match):
        foundName = match.group(1)

        if notHandled is not None:
            result = svars.get(foundName)
            if result is None:
                notHandled.add(foundName)
                return match.group(0)
            return result

        return svars.get(foundName, match.group(0))

    return _RE_SUBST_BUILTINVARS.sub(replaceVar, strval)

def substBuiltInVarsInParam(val, svars, splitListOfStrs = True, notHandled = None):
    """
    Return value with handled substitutions from a param of 'str',
    'list-of-strs' types or from a param of 'dict' with params of such types.
    """

    if not val:
        return val

    if isinstance(val, stringtype):
        return substBuiltInVars(val, svars, notHandled = notHandled)

    # This method should not allocate new memory for existing containers
    # in val if it can be avoided.

    extraArgs = {
        'svars': svars,
        'splitListOfStrs': splitListOfStrs,
        'notHandled': notHandled,
    }

    if isinstance(val, list):

        if not splitListOfStrs or any(not isinstance(x, stringtype) for x in val):
            result = [substBuiltInVarsInParam(x, **extraArgs) for x in val]
        else:
            # all items are strings
            result = []
            for item in val:
                if not mayHaveSubstVar(item):
                    result.append(item)
                    continue

                newVal = substBuiltInVars(item, svars, check = False,
                                            notHandled = notHandled)
                if not any(c in item for c in _USABLE_WHITESPACE):
                    result.extend(toList(newVal))
                else:
                    result.append(newVal)

        # use existing list and drop the new created one
        val[:] = result
        return val

    if isinstance(val, maptype):
        for k, v in val.items():
            val[k] = substBuiltInVarsInParam(v, **extraArgs)
        return val

    if isinstance(val, ConfNode):
        val.val = substBuiltInVarsInParam(val.val, **extraArgs)
        return val

    # buildconf should not use tuples for public elements
    assert not isinstance(val, tuple)
    return val

_HashAlgo = sha1

def setDefaultHashAlgo(algo):
    """
    Set default hash algo. Can be 'sha1' or 'md5'.
    """

    # pylint: disable = global-statement
    global _HashAlgo
    if algo == 'md5':
        _HashAlgo = wafutils.md5 = md5
    else:
        _HashAlgo = wafutils.md5 = sha1

def defaultHashAlgo():
    """
    Get default hash algo. Can be 'sha1' or 'md5'.
    """

    return _HashAlgo

# Since python 3.4 non-inheritable file handles are provided by default
if hasattr(os, 'O_NOINHERIT') and sys.hexversion < 0x3040000:
    def _hashFile(hashobj, path):
        # pylint: disable = no-member
        try:
            fd = os.open(path, os.O_BINARY | os.O_RDONLY | os.O_NOINHERIT)
        except OSError as pex:
            raise OSError('Cannot read from %r' % path) from pex

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
    _hash = _HashAlgo()
    return _hashFile(_hash, path).digest()

def hashFiles(paths):
    """
    Hash files from paths by using sha1/md5.
    Order of paths must be constant. Simple way to do it is to sort the path items.
    """

    # Old implementation (slower and less accurate):
    #_hash = 0
    #for path in paths:
    #    _hash = hashOrdObj((_hash, readFile(path, 'rb')))
    #return _hash

    _hash = _HashAlgo()
    for path in paths:
        _hashFile(_hash, path)
    return _hash.digest()

class BuildConfFunc(object):
    """
    Class to store a func from buildconf
    """

    __slots__ = ('func', 'name', '_filepath', '_startLN')

    def __init__(self, func):
        self.func = func
        self.name = func.__name__
        self._filepath = None
        self._startLN = None

    @property
    def filepath(self):
        """ Get file path where the function is """

        if self._filepath is None:
            func = self.func
            # the inspect.getabsfile exists but not documented
            filepath = inspect.getsourcefile(func) or inspect.getfile(func)
            if not os.path.isabs(filepath):
                filepath = os.path.abspath(filepath)
            self._filepath = filepath

        return self._filepath

    @property
    def startLN(self):
        """ Get line number in the file where the function is """

        if self._startLN is None:
            self._startLN = inspect.getsourcelines(self.func)[1]

        return self._startLN

    def __repr__(self):
        _repr = "%s:%s:%d" % (self.filepath, self.name, self.startLN)
        return _repr

if PLATFORM == 'windows':
    def lchown(path, user = -1, group = -1):
        """
        Change the owner/group of a path, raises an OSError if the
        ownership change fails.
        Do nothing on MS Windows.
        """

        # pylint: disable = unused-argument
        return
else:

    def lchown(path, user = -1, group = -1):
        """
        Change the owner/group of a path, raises an OSError if the
        ownership change fails.
        """

        import pwd
        import grp

        result = [user, group]
        for name, idx in (('user', 0), ('group', 1)):
            func = pwd.getpwnam if name == 'user' else grp.getgrnam

            if isinstance(result[idx], stringtype):
                try:
                    entry = func(result[idx])
                except KeyError as pex:
                    raise OSError('chown: unknown %s %r' % (name, user)) from pex
                if not entry: # just in case
                    raise OSError('chown: unknown %s %r' % (name, user)) from pex
                result[idx] = entry[2]

        return os.lchown(path, result[0], result[1])

wafutils.lchown = lchown

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
    This version supports preserving quoted substrings with spaces but it works
    slower than toListSimple does.
    Returns the object if not a string
    """
    if not isinstance(val, stringtype):
        return val

    if not ('"' in val or "'" in val): # optimization
        return val.split()

    # shlex.split worked quite well but did it too slowly

    # Actually manual algorithm should be faster but python regexp engine uses
    # some C code and therefore it works faster.
    return [stripQuotes(x) for x in _RE_TOLIST.split(val)[1::2]]

def uniqueListWithOrder(lst):
    """
    Return new list with preserved the original order of the list.
    Each element in lst must be hashable.
    """

    # pylint: disable = simplifiable-condition

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

def addRTLibPathsToOSEnv(paths, osenv):
    """
    Add runtime lib paths to OS environment depending on type of OS.
    Returns the osenv parameter.
    """

    def add(osenv, envname, vals):
        vals = os.pathsep.join(vals)
        paths = osenv.get(envname, '')
        if paths:
            paths = os.pathsep + paths
        osenv[envname] = vals + paths

    paths = toList(paths)
    if PLATFORM == 'windows':
        add(osenv, 'PATH', paths)
    else:
        add(osenv, 'LD_LIBRARY_PATH', paths)
        if PLATFORM == 'darwin':
            add(osenv, 'DYLD_LIBRARY_PATH', paths)

    return osenv

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
    except EnvironmentError as pex:
        raise ZenMakeError('Could not read the file %r' % str(modulePath)) from pex

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

class SafeCounter(object):
    """
    Thread safe counter
    """

    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()

    def increment(self, val = 1):
        ''' Increment value with lock '''
        with self._lock:
            self._value += val
            return self._value

    @property
    def value(self):
        ''' Get value '''
        return self._value

    @value.setter
    def value(self, val):
        ''' Set value with lock '''
        with self._lock:
            self._value = val

ProcCmdResult = struct('ProcCmdResult', 'exitcode, stdout, stderr')

class ProcCmd(object):
    """
    Class to run external command in a subprocess
    """

    def __init__(self, cmdLine, shell = False, captureOutput = False,
                                        stdErrToOut = True, outCallback = None):

        """
        Parameter outCallback can be used to handle stdout/stderr line by line
        without waiting for a process to exit. Also if outCallback is not None
        then it means that captureOutput is True. If stdErrToOut is True it means
        that captureOutput is True as well.
        """

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
        self._outCallback = outCallback
        self._proc = None
        self._timeoutExpired = False
        self._popenArgs = {
            'shell' : shell,
            'stdout' : None,
            'stderr' : None,
            'universal_newlines' : True,
        }

        if captureOutput or outCallback is not None:
            self._popenArgs['stdout'] = subprocess.PIPE
            self._popenArgs['stderr'] = subprocess.PIPE

        if stdErrToOut:
            self._popenArgs['stdout'] = subprocess.PIPE
            self._popenArgs['stderr'] = subprocess.STDOUT

        # start_new_session was added in python 3.2
        # Use 'start_new_session' to change the process(forked) group id to itself
        # so os.killpg with proc.pid can be used.
        # This parameter does nothing on Windows.
        self._popenArgs['start_new_session'] = True

    def _communicate(self):

        callback = self._outCallback
        if callback is None:
            stdout, stderr = self._proc.communicate()
            return ProcCmdResult(self._proc.returncode, stdout, stderr)

        # It is simple and actually not optimal algo but it works for ZenMake needs
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
        return ProcCmdResult(proc.returncode, None, None)

    def run(self, cwd = None, env = None, timeout = None):
        """
        Run command.
        Returns ProcCmdResult.
        """

        kwargs = self._popenArgs
        kwargs.update({
            'cwd' : cwd,
            'env' : env,
        })

        timer = None
        try:
            self._proc = subprocess.Popen(self._cmdLine, **kwargs)

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

            result = self._communicate()

            if self._timeoutExpired:
                raise ZenMakeProcessTimeoutExpired(self._origCmdLine, timeout,
                                                    result.stdout, result.stderr)

        except (OSError, subprocess.SubprocessError) as ex:
            raise ZenMakeError(str(ex)) from ex
        finally:
            if timer:
                timer.cancel()

            # release Popen object
            self._proc = None

        return result

def runCmd(cmdLine, cwd = None, env = None, shell = False, timeout = None,
            captureOutput = False, stdErrToOut = False, outCallback = None):
    """
    Run external command in a subprocess.
    Parameter outCallback can be used to handle stdout/stderr line by line
    without waiting for a process to exit. Also if outCallback is not None then
    it means that captureOutput is True. If stdErrToOut is True it means
    that captureOutput is True as well.
    Returns ProcCmdResult. If
    """

    # pylint: disable = too-many-arguments

    procCmd = ProcCmd(cmdLine, shell, captureOutput, stdErrToOut, outCallback)
    return procCmd.run(cwd, env, timeout)
