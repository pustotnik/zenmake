# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD, see LICENSE for more details.
"""

# Usually inheritance from built-in dict type is a bad idea. Especially if you 
# want to override __*item__ method. But here I want just to have dot notation and 
# auto creation of items. And this class for internal use only.
# I will remake this class if I get some problems with it.
class AutoDict(dict):

    def __init__(self, *args, **kwargs):
        super(AutoDict, self).__init__(*args, **kwargs)

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
