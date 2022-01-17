# coding=utf-8
#

"""
 Copyright (c) 2022 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import platform as _platform

from zm.constants import HOST_OS
from zm.pyutils import struct
from zm.pathutils import getNativePath

if HOST_OS == 'windows':
    def _getDefaultPrefix(dvars):
        return 'C:\\Program Files\\' + dvars.pkgname
else:
    def _getDefaultPrefix(_):
        return '/usr/local'

def _libDirPostfix():

    exists = os.path.exists
    if os.sep == '/' and _platform.architecture()[0] == '64bit' and \
        exists('/usr/lib64') and not exists('/usr/lib32'):

        return '64'

    return ''

LIBDIR_POSTFIX = _libDirPostfix()

VarConfig = struct('VarConfig', 'name, envname, desc, default')

CONFIG = (
    VarConfig(
        'prefix', 'PREFIX', 'installation prefix',
        _getDefaultPrefix
    ),
    VarConfig(
        'bindir', 'BINDIR', 'installation bin directory',
        lambda dvars: '%s/bin' % dvars.prefix
    ),
    VarConfig(
        'libdir', 'LIBDIR', 'installation lib directory',
        lambda dvars: '%s/lib%s' % (dvars.prefix, LIBDIR_POSTFIX)
    ),
)

VAR_NAMES = tuple(x.name for x in CONFIG)
VAR_ENVNAMES = tuple(x.envname for x in CONFIG)

class DirVars(object):
    """
    Provides various standard install directory variables as defined for GNU software.
    """

    def __init__(self, pkgname, clivars):

        self.pkgname = pkgname

        sep = os.sep
        isabs = os.path.isabs

        for item in CONFIG:
            val = clivars.get(item.name)
            # We must check val after clivars.get because this method uses 'default'
            # value only if an item doesn't exist while variable can exist but
            # can be None
            if val is None:
                val = item.default(self)
            val = getNativePath(val)
            if val and not isabs(val):
                val = sep + val

            setattr(self, item.name, val)

    def __getattr__(self, name):
        """
        It will only get called for undefined attributes
        and exists here mostly to mute pylint 'no-member' warning
        """
        raise self.__getattribute__(name)

    def get(self, name, default = None):
        """
        Get value by string name
        """
        return self.__dict__.get(name, default)

    def setAllInEnv(self, env):
        """
        Set all vars in the env
        """

        for item in CONFIG:
            env[item.envname] = self.get(item.name)
