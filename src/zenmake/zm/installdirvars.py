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
from zm.utils import substBuiltInVars

def _libDirPostfix():

    exists = os.path.exists
    if os.sep == '/' and _platform.architecture()[0] == '64bit' and \
        exists('/usr/lib64') and not exists('/usr/lib32'):

        return '64'

    return ''

LIBDIR_POSTFIX = _libDirPostfix()

VarConfig = struct('VarConfig', 'name, envname, default, desc, defaultdesc')

CONFIG = (
    VarConfig(
        'prefix', 'PREFIX', '/usr/local',
        'installation prefix',
    ),
    VarConfig(
        'execprefix', 'EXEC_PREFIX', '$(prefix)',
        'installation prefix for machine-specific files',
    ),
    VarConfig(
        'bindir', 'BINDIR', '$(execprefix)/bin',
        'installation directory for user executables',
    ),
    VarConfig(
        'sbindir', 'SBINDIR', '$(execprefix)/sbin',
        'installation directory for system executables',
    ),
    VarConfig(
        'libexecdir', 'LIBEXECDIR', '$(execprefix)/libexec',
        'installation directory for program executables',
    ),
    VarConfig(
        'libdir', 'LIBDIR', '$(execprefix)/lib%s' % LIBDIR_POSTFIX,
        'installation directory for object code libraries',
    ),
    VarConfig(
        'sysconfdir', 'SYSCONFDIR', '$(prefix)/etc',
        'installation directory for read-only single-machine data',
    ),
    VarConfig(
        'sharedstatedir', 'SHAREDSTATEDIR', '/var/lib',
        'installation directory for modifiable architecture-independent data',
    ),
    VarConfig(
        'localstatedir', 'LOCALSTATEDIR', '$(prefix)/var',
        'installation directory for modifiable single-machine data',
    ),
    VarConfig(
        'includedir', 'INCLUDEDIR', '$(prefix)/include',
        'installation directory for C header files',
    ),
    VarConfig(
        'datarootdir', 'DATAROOTDIR', '$(prefix)/share',
        'installation root directory for read-only architecture-independent data',
    ),
    VarConfig(
        'datadir', 'DATADIR', '$(datarootdir)',
        'installation directory for read-only architecture-independent data',
    ),
    VarConfig(
        'appdatadir', 'APPDATADIR', '$(datarootdir)/$(prjname)',
        'installation directory for read-only architecture-independent application data',
    ),
    VarConfig(
        'docdir', 'DOCDIR', '$(datarootdir)/doc/$(prjname)',
        'installation directory for documentation',
    ),
    VarConfig(
        'mandir', 'MANDIR', '$(datarootdir)/man',
        'installation directory for the man documentation',
    ),
    VarConfig(
        'infodir', 'INFODIR', '$(datarootdir)/info',
        'installation directory for the info documentation',
    ),
    VarConfig(
        'localedir', 'LOCALEDIR', '$(datarootdir)/locale',
        'locale-dependent data installation directory',
    ),
)

CONFIG_MAP = { item.name:item for item in CONFIG }

if HOST_OS == 'windows':
    CONFIG_MAP['prefix'].default = 'C:\\Program Files\\$(prjname)'
    for _name in ('bindir', 'sbindir', 'libexecdir', 'libdir'):
        CONFIG_MAP[_name].default = '$(execprefix)'

    for _name in ('sysconfdir', 'sharedstatedir', 'datarootdir'):
        CONFIG_MAP[_name].default = '$(prefix)'
    CONFIG_MAP['docdir'].default = '$(datarootdir)/doc'
    CONFIG_MAP['appdatadir'].default = '$(datarootdir)'

for _cfgitem in CONFIG:
    _cfgitem.defaultdesc = '[default: %s]' % _cfgitem.default

VAR_NAMES = tuple(x.name for x in CONFIG)
VAR_ENVNAMES = tuple(x.envname for x in CONFIG)

class DirVars(object):
    """
    Provides various standard install directory variables as defined for GNU software.
    """

    def __init__(self, prjname, clivars, getenv = os.environ.get):

        self.prjname = prjname

        sep = os.sep
        isabs = os.path.isabs

        for item in CONFIG:
            val = clivars.get(item.name)
            # We must check val after clivars.get because this method uses 'default'
            # value only if an item doesn't exist while variable can exist but
            # can be None
            if val is None:
                val = getenv(item.envname)
            if val is None:
                val = substBuiltInVars(item.default,
                                        svars = self.__dict__, check = False)
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

    def setAllTo(self, cont):
        """
        Copy all dir vars into a containter
        """

        for item in CONFIG:
            cont[item.envname] = self.get(item.name)
