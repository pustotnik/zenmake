# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

# pylint: disable = redefined-outer-name

from waflib.Tools import ifort
from zm.constants import PLATFORM

def configure(conf):
    """
    Configuration for ifort
    """

    ifort.configure(conf)

    # patch Waf module
    if PLATFORM != 'windows':
        conf.env.RPATH_ST = '-Wl,-rpath,%s'
