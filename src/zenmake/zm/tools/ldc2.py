# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

# pylint: disable = redefined-outer-name

from waflib.Errors import WafError
from waflib.Configure import conf
from waflib.Tools import ldc2

@conf
def find_ldc2(conf):
    """
    Find the program *ldc2* and set the variable *D*
    """
    # pylint: disable = invalid-name

    conf.find_program(['ldc2'], var = 'DC')
    # Waf uses D instead of DC
    conf.env.D = conf.env.DC

    try:
        out = conf.cmd_and_log(conf.env.DC + ['-version'])
    except WafError:
        conf.fatal("detected compiler is not ldc2")

    if out.find("LDC") == -1 and out.find("based on DMD v2.") == -1:
        conf.fatal("detected compiler is not ldc2")

def configure(conf):
    """
    Configuration for ldc2
    """

    ldc2.configure(conf)

    # patch Waf module
    conf.env.LINKFLAGS_dshlib  = ['-shared']
