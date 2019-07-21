# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from copy import deepcopy

try:
    from collections.abc import Mapping as maptype
except ImportError:
    from collections import Mapping as maptype

class AutoDict(dict):
    """
    Usually inheritance from built-in dict type is a bad idea. Especially if you
    want to override __*item__ methods. But here I want just to have dot notation and
    auto creation of items. And this class for internal use only.
    I will remake this class if I get some problems with it.
    """

    def __missing__(self, key):
        val = AutoDict()
        self[key] = val
        return val

    def __getattr__(self, name):
        # We can not use self.get to check value because value
        # can be any including None.
        if name not in self:
            val = AutoDict()
            self[name] = val
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __copy__(self):
        return AutoDict(self.copy())

    def __deepcopy__(self, memo):
        result = AutoDict()
        memo[id(self)] = result
        for k, v in self.items():
            result[deepcopy(k, memo)] = deepcopy(v, memo)
        # It's not really necessary to copy attrs
        #for k, v in self.__dict__.items():
        #    setattr(result, k, deepcopy(v, memo))
        return result

    def getByDots(self, keystring, default = None):
        """
        Get value using a dot notation string
        """
        keys = keystring.split('.')
        _dict = self
        for k in keys[:-1]:
            value = _dict.get(k, None)
            if value is None or not isinstance(value, maptype):
                return default
            _dict = value
        return _dict.get(keys[-1], default)
