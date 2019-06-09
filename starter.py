#!/usr/bin/env python
# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD, see LICENSE for more details.
"""

import sys, os
if sys.hexversion < 0x2070ef0:
    raise ImportError('Python >= 2.7 is required')

joinpath  = os.path.join

SCRIPTS_ROOTDIR = os.path.dirname(os.path.abspath(__file__))

WAF_DIR = joinpath(SCRIPTS_ROOTDIR, 'waf')
LIB_DIR = joinpath(SCRIPTS_ROOTDIR, 'lib')

sys.path.insert(1, WAF_DIR)
sys.path.insert(1, LIB_DIR)

def main():

    # Avoid writing .pyc files
    sys.dont_write_bytecode = True
    try:
        import buildconf
    except ImportError:
        from waflib import Logs
        Logs.init_log()
        Logs.error('Cannot import buildconf.py. Check that buildconf.py can be find in sys.path')
        sys.exit(1)
    sys.dont_write_bytecode = False

    import assist, utils

    if not os.path.exists(assist.BUILDROOT):
        os.makedirs(assist.BUILDROOT)
    if assist.BUILDSYMLINK and not os.path.exists(assist.BUILDSYMLINK):
        utils.mksymlink(assist.BUILDROOT, assist.BUILDSYMLINK)

    # We regard LIB_DIR as a directory where file 'wscript' is located
    utils.mksymlink(joinpath(LIB_DIR, 'wscript'), joinpath(assist.BUILDROOT, 'wscript'))

    utils.mksymlink(assist.SRCROOT, assist.SRCSYMLINK)

    # use of Options.lockfile is not enough
    os.environ['WAFLOCK'] = '.lock-wafbuild'
    from waflib import Options
    Options.lockfile = '.lock-wafbuild'
    from waflib import Scripting, Context, Build

    Build.BuildContext.execute = assist.autoconfigure(Build.BuildContext.execute)

    cwd = assist.BUILDROOT
    Scripting.waf_entry_point(cwd, Context.WAFVERSION, WAF_DIR)

    if(len(assist.wafcommands) == 1 and assist.wafcommands[0] == 'distclean'):
        assist.fullclean()

    return 0
