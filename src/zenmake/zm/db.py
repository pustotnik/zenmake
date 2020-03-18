# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import io

from waflib import ConfigSet
from zm.constants import PLATFORM
from zm.pyutils import texttype, PY2

try:
    _ascii = ascii
except NameError:
    _ascii = repr

class DBFile(object):
    """
    Class to save/load dict data to/from file.
    Not thread safe
    """

    __slots__ = ('_pathname', )

    def __init__(self, pathname):
        self._pathname = pathname

    def save(self, data, preserve = False):
        """
        Save data.
        If preserve is True then load old data before saving.
        """

        pathname = self._pathname

        if isinstance(data, ConfigSet.ConfigSet):
            data = data.get_merged_dict()
            data.pop('undo_stack', None)

        try:
            os.makedirs(os.path.dirname(pathname))
        except OSError:
            pass

        if preserve:
            try:
                _data = self.load()
            except EnvironmentError:
                pass
            else:
                _data.update(data)
                data = _data

        buff = []
        keys = sorted(data.keys())
        for key in keys:
            buff.append('%s = %s\n' % (key, _ascii(data[key])))

        tmppathname = pathname + '.tmp'
        with io.open(tmppathname, 'wt', encoding = "latin-1") as file:
            file.write(texttype(''.join(buff)))

        try:
            stat = os.stat(pathname)
            os.remove(pathname)
            if PLATFORM != 'windows':
                os.chown(tmppathname, stat.st_uid, stat.st_gid)
        except (AttributeError, OSError):
            pass

        os.rename(tmppathname, pathname)

    @staticmethod
    def saveTo(pathname, data, preserve = False):
        """
        Save data.
        If preserve is True then load old data before saving.
        """

        db = DBFile(pathname)
        db.save(data, preserve)

    def load(self, asConfigSet = False):
        """
        Load data
        """

        fname = self._pathname

        # python 3.x:
        #   function 'open' uses 'str' in text mode
        #   function 'io.open' uses 'str' in text mode
        #   'open' == 'io.open'
        # python 2.x:
        #   function 'open' uses 'str' in text mode
        #   function 'io.open' uses 'unicode' in text mode

        if PY2:
            with open(fname, 'rt') as file:
                body = file.read()
        else:
            # default encoding for 'open' in python 3.x is often 'utf-8'
            with open(fname, 'rt', encoding = "latin-1") as file:
                body = file.read()

        data = {}
        for reIt in ConfigSet.re_imp.finditer(body):
            # pylint: disable = eval-used
            grp = reIt.group
            data[grp(2)] = eval(grp(3))

        if asConfigSet:
            configSet = ConfigSet.ConfigSet()
            configSet.table = data
            data = configSet

        return data

    @staticmethod
    def loadFrom(pathname, asConfigSet = False):
        """
        Load data
        """

        db = DBFile(pathname)
        return db.load(asConfigSet)

    def exists(self):
        """ Return True if db file exists """
        return os.path.isfile(self._pathname)

    @staticmethod
    def dbexists(pathname):
        """ Return True if db file exists """
        db = DBFile(pathname)
        return db.exists()
