# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Errors import WafError

class ZenMakeError(WafError):
    """Base class for all ZenMake errors"""
    def __init__(self, *args, **kwargs):
        super(ZenMakeError, self).__init__(*args, **kwargs)
        self.fullmsg = self.verbose_msg
        delattr(self, 'verbose_msg')

class ZenMakeLogicError(WafError):
    """Some logic/prograaming error"""
