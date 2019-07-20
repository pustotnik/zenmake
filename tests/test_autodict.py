# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from copy import copy, deepcopy
import tests.common as cmn
from zm import autodict

class TestAutoDict(object):

    def testValues(self):
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

    def testCopy(self):
        AutoDict = autodict.AutoDict

        d1 = AutoDict(a = 1, b = AutoDict( aa = 2, bb = 3))
        d2 = copy(d1)
        assert d1 == d2

        d1.b.bb = 33
        assert d1 == d2

        d1.a = 11
        assert d1 != d2
        assert d2.a == 1

    def testDeepcopy(self):
        AutoDict = autodict.AutoDict

        d1 = AutoDict(a = 1, b = AutoDict( aa = 2, bb = 3))
        d2 = deepcopy(d1)
        assert d1 == d2

        d1.b.bb = 33
        assert d1 != d2
        assert d2.b.bb == 3