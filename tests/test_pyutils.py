# coding=utf-8
#

# pylint: disable = missing-docstring

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.pyutils import cachedprop, cached

def testCachedPropery():

    class Test:
        def __init__(self):
            self.funcCalled = False

        @cachedprop
        def value(self):
            self.funcCalled = True
            return 1 + 3

    test = Test()

    # first call
    assert not test.funcCalled
    assert test.value == 4
    assert test.funcCalled

    # next calls
    test.funcCalled = False
    assert test.value == 4
    assert not test.funcCalled
    assert test.value == 4
    assert not test.funcCalled

def testCachedRegFunc():

    cache = {}

    @cached
    def check1(var1, var2):
        nonlocal funcCalled
        funcCalled = True
        return var1 + var2

    funcCalled = False
    assert check1(1, 3) == 4
    assert funcCalled
    funcCalled = False
    assert check1(1, 3) == 4
    assert not funcCalled
    funcCalled = False
    assert check1(1, 3) == 4
    assert not funcCalled

    @cached(cache)
    def check2(var1, var2):
        nonlocal funcCalled
        funcCalled = True
        return var1 + var2

    funcCalled = False
    assert check2(1, 4) == 5
    assert funcCalled
    funcCalled = False
    assert check2(1, 4) == 5
    assert not funcCalled
    funcCalled = False
    assert check2(1, 4) == 5
    assert not funcCalled

def _checkCachedMethods(cls, fixture):

    obj = cls()

    for fname, params in fixture.items():
        func = getattr(obj, fname)
        args, expected = params

        # first call
        obj.funcCalled = False
        assert func(*args) == expected
        assert obj.funcCalled

        # next calls
        obj.funcCalled = False
        assert func(*args) == expected
        assert not obj.funcCalled
        obj.funcCalled = False
        assert func(*args) == expected
        assert not obj.funcCalled

def testCachedMethod():

    class ClassA:

        def __init__(self):
            self.funcCalled = False
            self.cache = {}

        @cached
        def check1(self):
            self.funcCalled = True

        @cached('cache')
        def check2(self):
            self.funcCalled = True
            return 1

        @cached('cache')
        def check3(self, var1):
            self.funcCalled = True
            return var1 + 10

        @cached('cache')
        def check4(self, var1):
            self.funcCalled = True
            return var1 + 20

    fixture = {
        'check1' : [(), None],
        'check2' : [(), 1],
        'check3' : [(4,), 14],
        'check4' : [(4,), 24],
    }
    _checkCachedMethods(ClassA, fixture)

    class ClassB:

        __slots__ = ('cache', 'funcCalled')
        def __init__(self):
            self.funcCalled = False
            self.cache = {}

        @cached
        def check1(self):
            self.funcCalled = True

        @cached('cache')
        def check2(self):
            self.funcCalled = True
            return 10

        @cached('cache')
        def check3(self, var1):
            self.funcCalled = True
            return var1 + 10

        @cached('cache')
        def check4(self, var1):
            self.funcCalled = True
            return var1 + 20

    fixture = {
        'check1' : [(), None],
        'check2' : [(), 10],
        'check3' : [(5,), 15],
        'check4' : [(5,), 25],
    }
    _checkCachedMethods(ClassB, fixture)
