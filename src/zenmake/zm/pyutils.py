# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Here are some extra stuff based on python only built-in ones.
"""

#pylint: disable=invalid-name,undefined-variable,unused-import

import sys
from collections.abc import Mapping, MutableMapping
maptype = Mapping

PY_MAJOR_VER = sys.version_info[0]
PY2 = PY_MAJOR_VER == 2
PY3 = PY_MAJOR_VER >= 3

stringtype = str # pragma: no cover
texttype = str # pragma: no cover
binarytype = bytes # pragma: no cover
_t = str # pragma: no cover

def _unicode(s):
    return s

def _encode(s):
    return s

def struct(typename, attrnames):
    """
    Generate simple and fast data class
    """

    attrnames = tuple(attrnames.replace(',', ' ').split())
    reprfmt = '(' + ', '.join(name + '=%r' for name in attrnames) + ')'

    def __init__(self, *args, **kwargs):
        if len(args) > len(attrnames):
            msg = "__init__() takes %d positional arguments but %d were given" \
                % (len(attrnames) + 1, len(args) + 1)
            raise AttributeError(msg)
        for name, value in zip(attrnames, args):
            setattr(self, name, value)
        for name, value in kwargs.items():
            if name not in attrnames:
                msg = "__init__() got an unexpected keyword argument '%s'" % name
                raise TypeError(msg)
            setattr(self, name, value)

    def __repr__(self):
        """ Return a nicely formatted representation string """
        return self.__class__.__name__ + \
                reprfmt % tuple(getattr(self, x) for x in attrnames)

    def __getattr__(self, name):
        """
        It will only get called for undefined attributes
        and exists here mostly to mute pylint 'no-member' warning
        """
        raise self.__getattribute__(name)

    namespace = {
        '__doc__'    : '%s(%s)' % (typename, attrnames),
        '__slots__'  : attrnames,
        '__init__'   : __init__,
        '__repr__'   : __repr__,
        '__getattr__': __getattr__,
    }
    result = type(typename, (object,), namespace)

    return result

def asmethod(cls, methodName = None, wrap = False, **kwargs):
    """
    Decorator to replace/attach/wrap method to any existing class
    """

    saveOrigAs = kwargs.get('saveOrigAs')

    def decorator(func):
        funcName = methodName if methodName else func.__name__
        if wrap:
            callOrigFirst = kwargs.get('callOrigFirst', True)
            origMethod = getattr(cls, funcName)

            if callOrigFirst:
                def execute(*args, **kwargs):
                    retval = origMethod(*args, **kwargs)
                    func(*args, **kwargs)
                    return retval
            else:
                def execute(*args, **kwargs):
                    func(*args, **kwargs)
                    return origMethod(*args, **kwargs)

            setattr(cls, funcName, execute)
        else:
            if saveOrigAs:
                origMethod = getattr(cls, funcName)
            setattr(cls, funcName, func)

        if saveOrigAs:
            setattr(cls, saveOrigAs, origMethod)
        return func

    return decorator
