# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Tools import ldc2

def configure(conf):
    """
    Configuration for dmd
    """

    ldc2.configure(conf)

    # patch Waf module
    conf.env.LINKFLAGS_dshlib  = ['-shared']
    #conf.env.LINKFLAGS_dstlib  = ['-static']
