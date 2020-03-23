# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import re
from os import path

from zm import ZENMAKE_DIR
from zm.constants import CAP_APPNAME
from zm.pypkg import PkgPath
from zm.cmd import Command as _Command

VERSION_FILE_NAME = 'version'
VERSION_FILE_PATH = path.join(ZENMAKE_DIR, VERSION_FILE_NAME)

#pylint: disable=line-too-long
# from https://semver.org/
SEMVER_RE = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
#pylint: enable=line-too-long

def parseVersion(ver):
    """ Return result of re.match """
    return re.match(SEMVER_RE, ver)

def checkFormat(ver):
    """ check format of version """
    return bool(parseVersion(ver))

def _readLastSaved():
    verFile = VERSION_FILE_PATH
    pkgPath = PkgPath(verFile)
    if not pkgPath.isfile():
        raise RuntimeError('File with version %r is not found' % verFile)

    lines = []
    ver = None
    with pkgPath.openText() as file:
        lines = file.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        ver = str(line) # convert from unicode in python 2.x
        break

    if not ver:
        raise RuntimeError('Version in file %r was not found' % verFile)

    if not checkFormat(ver):
        raise RuntimeError('Version %r has invalid format' % ver)

    return ver

_LAST_SAVED_VERSION = _readLastSaved()

def current():
    """ Get current version """
    return _LAST_SAVED_VERSION

def isDev():
    """ Detect that this is development version """

    return current().endswith('dev')

class Command(_Command):
    """
    Print version of the program.
    It's implementation of command 'version'.
    """

    def _run(self, cliArgs):

        msg = "{} version {}".format(CAP_APPNAME, current())
        if cliArgs.verbose >= 1:
            import platform as _platform
            from waflib.Context import WAFVERSION
            msg += '\nWaf version: %s' % WAFVERSION
            msg += '\nPython version: %s' % _platform.python_version()
            msg += '\nPython implementation: %s' % _platform.python_implementation()

        self._info(msg)
        return 0
