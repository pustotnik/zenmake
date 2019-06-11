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
        self.parent = None

    def __missing__(self, key):
        return AutoDict()

    def __getattr__(self, name):
        if name == 'parent':
            return super(AutoDict, self).__getattr__(name)
        
        val = self.get(name, None)
        if val is None:
            self[name] = AutoDict()
            self[name].parent = self
            return self[name]
        else:
            return val

    def __setattr__(self, name, value):
        if name == 'parent':
            super(AutoDict  , self).__setattr__(name, value)
        else:
            self[name] = value
