# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import Logs

if not Logs.log:
    Logs.init_log() # pragma: no cover

enableColors = Logs.enable_colors
colors = Logs.colors

debug  = Logs.debug
error  = Logs.error
warn   = Logs.warn
info   = Logs.info
pprint = Logs.pprint

def verbose():
    """
    Wrapper of Logs.verbose
    """
    return Logs.verbose
