# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import tempfile
import shutil
import atexit
from contextlib import contextmanager
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import starter

_tempdirs = []

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
    path = tempfile.mkdtemp(prefix = 'zenmake.tests.')
    _tempdirs.append(path)
    return path

def removeAllTmpDirsForTests():
    for path in _tempdirs:
        shutil.rmtree(path)
    del _tempdirs[:]

atexit.register(removeAllTmpDirsForTests)

SHARED_TMP_DIR = makeTmpDirForTests()
#TEST_PROJECTS_DIR = os.path.join(SHARED_TMP_DIR, 'projects')