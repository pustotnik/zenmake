# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

# pylint: disable = redefined-outer-name

from waflib.Errors import WafError
from waflib.Configure import conf
from waflib.Tools import dmd

@conf
def find_dmd(conf):
    """
    Find the program *dmd*, or *dmd2* and set the variable *D*
    """
    # pylint: disable = invalid-name

    conf.find_program(['dmd', 'dmd2'], var = 'DC')
    # Waf uses D instead of DC
    conf.env.D = conf.env.DC

    # make sure that we're dealing with dmd1, dmd2
    try:
        out = conf.cmd_and_log(conf.env.DC + ['--version'])
    except WafError:
        conf.fatal("detected compiler is not dmd")

    if out.find("D Compiler v") == -1 or out.find("LDC") >= 0:
        conf.fatal("detected compiler is not dmd")

def configure(conf):
    """
    Configuration for dmd
    """

    dmd.configure(conf)

    # patch Waf module
    conf.env.LINKFLAGS_dshlib  = ['-shared']
