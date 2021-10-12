# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

class AnyStrKey(object):
    """ Any amount of string keys"""
    __slots__ = ()

    def __eq__(self, other):
        if not isinstance(other, AnyStrKey):
            # don't attempt to compare against unrelated types
            return NotImplemented # pragma: no cover
        return True

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash(self.__class__)

ANYSTR_KEY = AnyStrKey()

def addSelectToParams(scheme, paramNames = None):
    """
    Add '.select' variant to param from scheme
    """

    if paramNames is None:
        paramNames = tuple(scheme.keys())

    for name in paramNames:
        origParam = scheme[name]
        scheme['%s.select' % name] = {
            'type' : 'dict',
            'vars' : {
                'default' : origParam,
                ANYSTR_KEY : origParam,
            },
        }
