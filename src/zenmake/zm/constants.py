# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.utils import platform as _platform

APPNAME = 'zenmake'
BUILDOUTNAME = 'out'
WAF_CACHE_DIRNAME = 'c4che'
WAF_CACHE_NAMESUFFIX = '_cache.py'
ZENMAKE_CACHE_NAMESUFFIX = '.%s.py' % APPNAME
ZENMAKE_COMMON_FILENAME = '.%s-common' % APPNAME
WSCRIPT_NAME = 'zmwscript'

PLATFORM = _platform()
KNOWN_PLATFORMS = (
    'linux', 'windows', 'darwin', 'freebsd', 'openbsd', 'sunos', 'cygwin',
    'msys', 'riscos', 'atheos', 'os2', 'os2emx', 'hp-ux', 'hpux', 'aix', 'irix',
)

if PLATFORM == 'windows':
    EXE_FILE_EXTS = '.exe,.com,.bat,.cmd'
else:
    EXE_FILE_EXTS = ',.sh,.pl,.py'
