# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.pyutils import struct

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

_PATHS_SCHEME_DICT_VARS = {
    'incl'       : { 'type': ('str', 'list-of-strs') },
    'excl'       : { 'type': ('str', 'list-of-strs') },
    'ignorecase' : { 'type': 'bool' },
    'startdir'   : { 'type': 'str' },
}

PATHS_SCHEME = {
    'type' : ('str', 'list', 'dict'),
    'dict' : {
        'vars' : _PATHS_SCHEME_DICT_VARS,
    },
    'list' : {
        'vars-type' : ('str', 'dict'),
        'dict-vars' : _PATHS_SCHEME_DICT_VARS,
    },
    'traits' : ['complex-path'],
}

ConfNode = struct('ConfNode', 'val, traits')
