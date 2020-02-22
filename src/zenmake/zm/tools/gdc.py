# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

# pylint: disable = redefined-outer-name

from waflib.Errors import WafError
from waflib.Configure import conf
from waflib.Tools import gdc

@conf
def find_gdc(conf):
    """
    Find the program *gdc* and set the variable *D*
    """
    # pylint: disable = invalid-name

    conf.find_program(['gdc'], var = 'DC')
    # Waf uses D instead of DC
    conf.env.D = conf.env.DC

    try:
        out = conf.cmd_and_log(conf.env.DC + ['--version'])
    except WafError:
        conf.fatal("detected compiler is not gdc")

    if out.find("gdc") == -1:
        conf.fatal("detected compiler is not gdc")

configure = gdc.configure
