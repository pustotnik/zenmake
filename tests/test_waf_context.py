# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = no-member

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from zm.pyutils import maptype
from zm.waf.context import WafContext

def testZmCache():

    ctx = WafContext(run_dir = os.getcwd())

    cache = ctx.zmcache()
    assert isinstance(cache, maptype)
    assert not cache

    cache['ttt'] = 'test val'
    assert ctx.zmcache()['ttt'] == cache['ttt']
