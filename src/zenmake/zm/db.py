# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import io
import pickle

from waflib import ConfigSet
from zm.constants import PLATFORM
from zm.pyutils import texttype, PY_MAJOR_VER
from zm.utils import configSetToDict

_MSGPACK_EXISTS = False
try:
    import msgpack
    _MSGPACK_EXISTS = True
except ImportError:
    pass

# use fixed proto to avoid problems with upgrading/downgrading of python
_PICKLE_PROTOCOL = 4 # version 4 was added in python 3.4

class DBFile(object):
    """
    General class to save/load dict data to/from file.
    """

    __slots__ = ('_pathname', '_extension')

    def __init__(self, pathname, extension):
        self._extension = extension
        self._pathname = os.path.abspath(pathname + extension)

    @staticmethod
    def _asConfigSet(data):
        configSet = ConfigSet.ConfigSet()
        configSet.table = data
        return configSet

    @property
    def path(self):
        """ Get real path """
        return self._pathname

    @property
    def extension(self):
        """ Get file extension """
        return self._extension

    def save(self, data):
        """ Save dict data """

        if isinstance(data, ConfigSet.ConfigSet):
            data = configSetToDict(data)

        try:
            os.makedirs(os.path.dirname(self.path))
        except OSError:
            pass

        self._save(data)

    def load(self, asConfigSet = False):
        """ Load dict data """

        data = self._load()
        if asConfigSet:
            return self._asConfigSet(data)
        return data

    def exists(self):
        """ Return True if db file exists """
        return os.path.isfile(self.path)

    def _save(self, data):
        raise NotImplementedError

    def _load(self):
        raise NotImplementedError

class PyDBFile(DBFile):
    """
    Implemetation of DBFile to save/load python dicts in text format
    Not thread safe
    """

    __slots__ = ()

    def __init__(self, pathname, extension = None):
        extension = '.pydict' if extension is None else extension
        super(PyDBFile, self).__init__(pathname, extension)

    def _save(self, data):
        """ Save to file """

        buff = []
        keys = sorted(data.keys())
        for key in keys:
            buff.append('%s = %s\n' % (key, ascii(data[key])))
        dump = ''.join(buff)

        pathname = self._pathname

        tmppathname = pathname + '.tmp'
        with io.open(tmppathname, 'wt', encoding = "latin-1") as file:
            file.write(texttype(dump))

        try:
            stat = os.stat(pathname)
            os.remove(pathname)
            if PLATFORM != 'windows':
                os.chown(tmppathname, stat.st_uid, stat.st_gid)
        except (AttributeError, OSError):
            pass

        os.rename(tmppathname, pathname)

    def _load(self):
        """ Load from file """

        fname = self._pathname

        # python 3.x:
        #   function 'open' uses 'str' in text mode
        #   function 'io.open' uses 'str' in text mode
        #   'open' == 'io.open'
        # python 2.x:
        #   function 'open' uses 'str' in text mode
        #   function 'io.open' uses 'unicode' in text mode

        # default encoding for 'open' in python 3.x is often 'utf-8'
        with open(fname, 'rt', encoding = "latin-1") as file:
            dump = file.read()

        data = {}
        for reIt in ConfigSet.re_imp.finditer(dump):
            # pylint: disable = eval-used
            grp = reIt.group
            data[grp(2)] = eval(grp(3))
        return data

_BINDB_FILEEXT_FORMAT = "." + PLATFORM + "%s"

class _DBFileGen(DBFile):

    __slots__ = ('_module', '_dumpArgs', '_loadArgs')

    def __init__(self, pathname, module, extension, **kwargs):

        if not extension:
            extension = ''
        # to avoid problems with different platforms
        extension = _BINDB_FILEEXT_FORMAT % extension

        self._module = module
        self._dumpArgs = kwargs.get('dumpArgs', ([],{}))
        self._loadArgs = kwargs.get('loadArgs', ([],{}))

        super(_DBFileGen, self).__init__(pathname, extension)

    def _save(self, data):
        """ Save to file """

        args, kwargs = self._dumpArgs
        dump = self._module.dumps(data, *args, **kwargs)

        pathname = self._pathname

        tmppathname = pathname + '.tmp'
        with open(tmppathname, 'wb') as file:
            file.write(dump)

        try:
            stat = os.stat(pathname)
            os.remove(pathname)
            if PLATFORM != 'windows':
                os.chown(tmppathname, stat.st_uid, stat.st_gid)
        except (AttributeError, OSError):
            pass

        os.rename(tmppathname, pathname)

    def _load(self):
        """ Load from file """

        with open(self._pathname, 'rb') as file:
            dump = file.read()

        args, kwargs = self._loadArgs
        return self._module.loads(dump, *args, **kwargs)

_PICKLE_ARGS = {
    'dumpArgs' : ([_PICKLE_PROTOCOL], {}),
    'loadArgs' : ([], {}),
}

class PickleDBFile(_DBFileGen):
    """
    Implemetation of DBFile to save/load python dicts in python pickle format
    """

    __slots__ = ()

    def __init__(self, pathname, extension = None):
        module = pickle
        # To avoid compatible problems it's better to use different extensions
        # for different python versions
        extension = '.pickle%d' % PY_MAJOR_VER if extension is None else extension
        super(PickleDBFile, self).__init__(pathname, module, extension,
                                           **_PICKLE_ARGS)

if _MSGPACK_EXISTS:
    _MSGPACK_ARGS = {
        'dumpArgs' : ([], { 'use_bin_type' : True }),
        'loadArgs' : ([], { 'raw' : False }),
    }

    class MsgpackDBFile(_DBFileGen):
        """
        Implemetation of DBFile to save/load python dicts in msgpack format
        """

        __slots__ = ()

        def __init__(self, pathname, extension = None):
            module = msgpack
            extension = '.msgpack' if extension is None else extension
            super(MsgpackDBFile, self).__init__(pathname, module, extension,
                                                **_MSGPACK_ARGS)

_defaultDbFormat = 'py'

def useformat(dbformat):
    """ Set default DB format """

    if dbformat == 'msgpack' and not _MSGPACK_EXISTS:
        dbformat = 'pickle'

    # pylint: disable = global-statement
    global _defaultDbFormat
    _defaultDbFormat = dbformat

def getformat():
    """ Get default DB format """
    return _defaultDbFormat

def factory(pathname, dbformat = None):
    """
    Create DBFile instance by dbformat
    """

    if dbformat is None:
        dbformat = _defaultDbFormat

    implClsName = '%sDBFile' % dbformat.capitalize()
    return globals()[implClsName](pathname)

def saveTo(pathname, data):
    """ Save data to db in current format """
    factory(pathname).save(data)

def loadFrom(pathname, asConfigSet = False):
    """ Load data from db in current format """
    return factory(pathname).load(asConfigSet)

def exists(pathname):
    """ Return True if db file exists """
    return factory(pathname).exists()

def realpath(pathname):
    """ Return real path of db in current format """
    return factory(pathname).path
