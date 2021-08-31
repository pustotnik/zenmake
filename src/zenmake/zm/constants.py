# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import platform
from zm.utils import platform as _platform

APPNAME = 'zenmake'
CAP_APPNAME = 'ZenMake'
AUTHOR = 'Alexander Magola'
COPYRIGHT_ONE_LINE = '2019 - present %s' % AUTHOR

PYTHON_EXE = sys.executable if sys.executable else 'python3'

DEPNAME_DELIMITER = ':'
DEFAULT_BUILDROOTNAME = 'build'
DEFAULT_BUILDWORKNAME = '@bld'
#BUILDOUTNAME = 'out'
BUILDOUTNAME = ''
CONFTEST_DIR_PREFIX = '.cfgchk'
WAF_CACHE_DIRNAME = 'c4che'
WAF_CACHE_NAMESUFFIX = '_cache.py'
WAF_CONFIG_LOG = 'config.log'
WAF_CFG_FILES_ENV_KEY = 'cfg_files'
ZENMAKE_CONF_CACHE_PREFIX = 'conf.cache'
ZENMAKE_BUILDMETA_FILENAME = '.buildmeta'
WAF_LOCKFILE = ZENMAKE_BUILDMETA_FILENAME
BUILDCONF_NAME = 'buildconf'
BUILDCONF_EXTS = ['.py', '.yaml', '.yml']
BUILDCONF_FILENAMES = ['%s%s' % (BUILDCONF_NAME, x) for x in BUILDCONF_EXTS]

INVALID_BUILDTYPES = (WAF_CONFIG_LOG, WAF_CACHE_DIRNAME, WAF_LOCKFILE)

TASK_TARGET_KINDS = frozenset(('stlib', 'shlib', 'program'))

CWD = os.getcwd()
PLATFORM = _platform()
KNOWN_PLATFORMS = (
    'linux', 'windows', 'darwin', 'freebsd', 'openbsd', 'sunos', 'cygwin',
    'msys', 'riscos', 'atheos', 'os2', 'os2emx', 'hp-ux', 'hpux', 'aix', 'irix',
)
CPU_ARCH = platform.machine()

if PLATFORM == 'windows':
    EXE_FILE_EXTS = '.exe,.com,.bat,.cmd'
else:
    EXE_FILE_EXTS = ',.sh,.pl,.py'

if PLATFORM == 'windows':
    SYSTEM_LIB_PATHS = []
else:
    SYSTEM_LIB_PATHS = ['/usr/lib64', '/usr/lib', '/usr/local/lib64', '/usr/local/lib']

PROTECTED_DYN_SUBSTVARS = ('PREFIX', 'BINDIR', 'LIBDIR', 'DESTDIR',
    'PROJECT_NAME', 'TOP_DIR', 'BUILDROOT_DIR', 'BUILDTYPE_DIR',
    'TGT', 'SRC',
)
