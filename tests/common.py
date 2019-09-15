# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import types
import string
import random
import tempfile
import shutil
import atexit
from contextlib import contextmanager
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from zm import utils
from zm import pyutils
from tests import ZENMAKE_DIR

_tempdirs = []

def randomstr(length = 20, withDigits = False):
    letters = string.ascii_lowercase
    if withDigits:
        letters += string.digits
    return ''.join(random.choice(letters) for i in range(length))

def randomint(minVal = 0, maxVal = 2 ** 32):
    return random.randint(minVal, maxVal)

@contextmanager
def capturedOutput():
    newout, newerr = StringIO(), StringIO()
    oldout, olderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = newout, newerr
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = oldout, olderr

def makeTmpDirForTests():
    path = tempfile.mkdtemp(prefix = 'zm.tests.')
    _tempdirs.append(path)
    return path

def removeAllTmpDirsForTests():
    for path in _tempdirs:
        shutil.rmtree(path)
    del _tempdirs[:]

def asRealConf(_buildconf):
    buildconf = types.ModuleType('buildconf')
    buildconf.__file__ = os.path.abspath('buildconf.py')

    # For in case I convert all AutoDict objects into dict ones
    # It ensures that there are no any side effects of AutoDict

    def toDict(_dict):
        for k, v in _dict.items():
            if isinstance(v, pyutils.maptype):
                toDict(v)
                _dict[k] = dict(v)

    for k, v in _buildconf.items():
        if isinstance(v, pyutils.maptype):
            v = dict(v)
            setattr(buildconf, k, v)
            toDict(v)
        else:
            setattr(buildconf, k, v)
    return buildconf

atexit.register(removeAllTmpDirsForTests)

PLATFORM = utils.platform()
SHARED_TMP_DIR = makeTmpDirForTests()
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PROJECTS_DIR = os.path.join(TESTS_DIR, 'projects')
