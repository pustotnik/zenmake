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

def testValues():
    AutoDict = autodict.AutoDict
    d = AutoDict()
    d['test'] = 10
    assert d == {'test' : 10}
    assert hasattr(d, 'test')
    assert d['test'] == d.test

    assert 'something' not in d
    d.something = 123
    assert 'something' in d

    assert not d.test2
    assert not d['test3'].test4

    d2 = AutoDict(dict(a = 1, b = 2))
    assert d2 == dict(a = 1, b =2)

    d2 = AutoDict(dict(a = 1, b = dict(aa = 3, bb = 4)))
    assert d2 == dict(a = 1, b = dict(aa = 3, bb = 4))

    d2 = AutoDict()
    d2.a.b.c = 1
    assert d2 == dict(a = dict(b = dict(c = 1)))

def testCopy():
    AutoDict = autodict.AutoDict

    d1 = AutoDict(a = 1, b = AutoDict( aa = 2, bb = 3))
    d2 = copy(d1)
    assert d1 == d2

    d1.b.bb = 33
    assert d1 == d2

    d1.a = 11
    assert d1 != d2
    assert d2.a == 1

def testDeepcopy():
    AutoDict = autodict.AutoDict

    d1 = AutoDict(a = 1, b = AutoDict( aa = 2, bb = 3))
    d2 = deepcopy(d1)
    assert d1 == d2

    d1.b.bb = 33
    assert d1 != d2
    assert d2.b.bb == 3

def testGetByDots():
    AutoDict = autodict.AutoDict

    d = AutoDict(a = 1)
    assert d.getByDots('a') == 1
    assert d.getByDots('a.b') == None

    d = AutoDict(a = dict(b = 2))
    assert d.getByDots('a') == dict(b = 2)
    assert d.getByDots('a.b') == 2
    assert d.getByDots('a.b.c') == None
    assert d.getByDots('a.b.c.d') == None