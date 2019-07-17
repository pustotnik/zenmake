# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import tests.common as cmn
from zm import autodict

class TestAutoDict(object):
    def testAll(self):
        d = autodict.AutoDict()
        d['test'] = 10
        assert d == {'test' : 10}
        assert hasattr(d, 'test')
        assert d['test'] == d.test

        assert 'something' not in d
        d.something = 123
        assert 'something' in d

        assert not d.test2
        assert not d['test3'].test4

        d2 = autodict.AutoDict(dict(a = 1, b =2))
        assert d2 == dict(a = 1, b =2)