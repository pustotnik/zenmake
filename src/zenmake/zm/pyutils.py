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

class _HashedSeq(list):

    __slots__ = ('hashvalue',)

    def __init__(self, vals):
        # pylint: disable = super-init-not-called
        self[:] = vals
        self.hashvalue = hash(vals)

    def __hash__(self):
        return self.hashvalue

def _makeCacheKey(prefix, args, kwargs, kwargsmark = (object(),), fasttypes = (int, str) ):

    key = (prefix,) + args

    if kwargs:
        key += kwargsmark
        for item in kwargs.items():
            key += item

    if len(key) == 1:
        return key[0]
    if len(key) == 2 and type(key[1]) in fasttypes:
        return key

    return _HashedSeq(key)

class cached(object):
    """
    Decoarator to cache a result of a function/method. Sometimes called "memoize".
    Similar to @cache from python >= 3.9 but allows to set custom cache holder
    and doesn't keep custom cache holder for object methods 'forever'.
    """

    def __init__(self, cacheattr = None):

        self.cacheName = None

        if callable(cacheattr):
            self.cache = {}
            self.func     = cacheattr
            self.__name__ = self.func.__name__
            self.__doc__  = self.func.__doc__
            self._inited  = True
            return

        self.func      = None
        self.__name__  = ''
        self.__doc__   = ''
        self._inited   = False

        if cacheattr is None:
            self.cache = {}
        elif isinstance(cacheattr, stringtype):
            self.cache = None
            self.cacheName = cacheattr
        else:
            self.cache = cacheattr

    def __call__(self, *args, **kwargs):

        if not self._inited:
            self.func     = args[0]
            self.__name__ = self.func.__name__
            self.__doc__  = self.func.__doc__
            self._inited  = True

            return self

        return self._eval(None, self.cache, args, kwargs)

    def _eval(self, fromobj, cache, args, kwargs):

        key = _makeCacheKey(id(self.func), args, kwargs)

        try:
            val = cache.get(key, _NOT_FOUND)
        except AttributeError:
            if not fromobj and self.cacheName:
                msg = "String name for cache attribute cannot be used "
                msg += "for regular function %r " % self.func.__name__
                raise TypeError(msg) from None
            raise

        if val is _NOT_FOUND:
            if fromobj is None:
                val = self.func(*args, **kwargs)
            else:
                val = self.func(fromobj, *args, **kwargs)
            cache[key] = val

        return val

    def __get__(self, obj, owner = None):

        if obj is None:
            return self

        if self.cache is None:
            # don't save cache from an object in self.cache
            # otherwise it will keep/hold cached values 'forever'
            try:
                cache = getattr(obj, self.cacheName)
            except AttributeError:
                cache = {}
                setattr(obj, self.cacheName, cache)
        else:
            cache = self.cache

        def wrapper(*args, **kwargs):
            return self._eval(obj, cache, args, kwargs)

        dictAttr = getattr(obj, '__dict__', None)
        if dictAttr is not None:
            # optimization for next calls: set method to the obj directly
            wrapper.cache    = self.cache
            wrapper.__name__ = self.func.__name__
            wrapper.__doc__  = self.func.__doc__
            dictAttr[self.__name__] = wrapper

        return wrapper
