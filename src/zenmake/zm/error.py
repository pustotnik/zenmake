# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Errors import WafError as _WafError

class ZenMakeError(_WafError):
    """Base class for all ZenMake errors"""
    def __init__(self, *args, **kwargs):
        super(ZenMakeError, self).__init__(*args, **kwargs)
        self.fullmsg = self.verbose_msg

class ZenMakeLogicError(ZenMakeError):
    """Some logic/programming error"""

class ZenMakeConfError(ZenMakeError):
    """Invalid buildconf fle error"""

class ZenMakeConfTypeError(ZenMakeConfError):
    """Invalid buildconf param type error"""

class ZenMakeConfValueError(ZenMakeConfError):
    """Invalid buildconf param value error"""
