# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.pyutils import stringtype

class AnyAmountStrsKey(object):
    """ Any amount of string keys"""
    __slots__ = ()

    def __eq__(self, other):
        if not isinstance(other, AnyAmountStrsKey):
            # don't attempt to compare against unrelated types
            return NotImplemented # pragma: no cover
        return True

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash(self.__class__)

ANYAMOUNTSTRS_KEY = AnyAmountStrsKey()

def addSelectToParams(scheme, paramNames = None):
    """
    Add '.select' variant to param from scheme
    """

    if paramNames is None:
        paramNames = tuple(scheme.keys())
    elif isinstance(paramNames, stringtype):
        paramNames = tuple(paramNames)

    for name in paramNames:
        origParam = scheme[name]
        scheme['%s.select' % name] = {
            'type' : 'dict',
            'vars' : {
                'default' : origParam,
                ANYAMOUNTSTRS_KEY : origParam,
            },
        }
