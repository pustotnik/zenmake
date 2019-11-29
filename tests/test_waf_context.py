# coding=utf-8
#

# _pylint: skip-file
# pylint: disable = wildcard-import, unused-wildcard-import, unused-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation
# pylint: disable = no-member

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import pytest

from waflib.ConfigSet import ConfigSet
from waflib.Context import Context
import tests.common as cmn
from zm.autodict import AutoDict
from zm.waf import context

def testLoadTasksFromCache(tmpdir):

    ctx = Context(run_dir = os.getcwd())

    cachefile = tmpdir.join("cachefile")
    assert ctx.loadTasksFromFileCache(str(cachefile)) == {}

    #ctx = Context()
    cachedata = ConfigSet()
    cachedata.something = 11
    cachedata.store(str(cachefile))
    assert ctx.loadTasksFromFileCache(str(cachefile)) == {}

    #ctx = Context()
    cachedata.zmtasks = dict( a = 1, b = 2 )
    cachedata.store(str(cachefile))
    assert ctx.loadTasksFromFileCache(str(cachefile)) == cachedata.zmtasks

    cachedata.zmtasks = dict( a = 3, b = 4 )
    cachedata.store(str(cachefile))
    assert ctx.loadTasksFromFileCache(str(cachefile)) == cachedata.zmtasks
