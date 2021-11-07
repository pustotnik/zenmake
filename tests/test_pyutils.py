# coding=utf-8
#

# pylint: disable = missing-docstring

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.pyutils import cachedprop

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
