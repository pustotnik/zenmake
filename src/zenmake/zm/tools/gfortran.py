# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

# pylint: disable = redefined-outer-name

from waflib.Tools import gfortran

def configure(conf):
    """
    Configuration for gfortran
    """

    gfortran.configure(conf)

    # patch Waf module
    del conf.env.FCFLAGS_DEBUG
    conf.env.RPATH_ST = '-Wl,-rpath,%s'
