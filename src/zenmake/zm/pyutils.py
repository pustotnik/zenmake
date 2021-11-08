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

        if isinstance(func, cachedprop):
            if methodName:
                func.attrname = methodName
            funcName = func.attrname
        else:
            funcName = methodName if methodName else func.__name__

        if wrap or saveOrigAs:
            origMethod = getattr(cls, funcName)

        if wrap:
            if kwargs.get('callOrigFirst', True):
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
            setattr(cls, funcName, func)

        if saveOrigAs:
            setattr(cls, saveOrigAs, origMethod)
        return func

    return decorator

_NOT_FOUND = object()

class cachedprop(object):
    """
    Decorator for cached read-only properties.
    Notice that it cannot be used with __slots__.

    Anyway, the standard implementation of @cached_property from python >=3.8
    has some perf problem with locks: https://bugs.python.org/issue43468
    This implementation doesn't use locks and it is thread safe while
    implementation of cached property method is thread safe.
    """

    def __init__(self, fget):
        self.fget     = fget
        self.attrname = fget.__name__
        self.__doc__  = fget.__doc__

    def __get__(self, obj, owner = None):

        if obj is None:
            return self

        try:
            cache = obj.__dict__
        except AttributeError:
            msg = "No '__dict__' attribute on %r " % type(obj).__name__
            raise TypeError(msg) from None

        value = cache.get(self.attrname, _NOT_FOUND)
        if value is _NOT_FOUND:
            value = cache[self.attrname] = self.fget(obj)

        return value
