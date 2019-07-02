#!/usr/bin/env python
# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys 
import os
if sys.hexversion < 0x2070ef0:
    raise ImportError('Python >= 2.7 is required')

joinpath  = os.path.join

SCRIPTS_ROOTDIR = os.path.dirname(os.path.abspath(__file__))

WAF_DIR = joinpath(SCRIPTS_ROOTDIR, 'waf')
LIB_DIR = joinpath(SCRIPTS_ROOTDIR, 'lib')
ARGPARSE_DIR = joinpath(SCRIPTS_ROOTDIR, 'argparse')

sys.path.insert(1, WAF_DIR)
sys.path.insert(1, LIB_DIR)
# argparse from the https://pypi.org/project/argparse/ supports alieses
sys.path.insert(1, ARGPARSE_DIR)

def main():

    # When set to a non-empty value, the process will not search for a build 
    # configuration in upper folders.
    os.environ['NOCLIMB'] = '1'

    # use of Options.lockfile is not enough
    os.environ['WAFLOCK'] = '.lock-wafbuild'
    from waflib import Options
    Options.lockfile = '.lock-wafbuild'
    from waflib import Scripting, Context, Build, Logs

    import assist
    import utils
    import cli

    def prepareDirs():    
        if not os.path.exists(assist.BUILDROOT):
            os.makedirs(assist.BUILDROOT)
        if assist.BUILDSYMLINK and not os.path.exists(assist.BUILDSYMLINK):
            utils.mksymlink(assist.BUILDROOT, assist.BUILDSYMLINK)

        # We regard LIB_DIR as a directory where file 'wscript' is located
        utils.mksymlink(joinpath(LIB_DIR, 'wscript'), 
                        joinpath(assist.BUILDROOT, 'wscript'))

        utils.mksymlink(assist.SRCROOT, assist.SRCSYMLINK)
    
    wafCmdLine = cli.parseAll(sys.argv)

    if assist.isBuildConfFake():
        Logs.error('Config buildconf.py not found. Check buildconf.py '
                            'exists in the project directory.')
        sys.exit(1)
    
    # Special case for 'distclean'
    cmd = cli.selected
    if cmd.name == 'distclean':
        assist.distclean()
        return 0

    if cmd.args.distclean:
        assist.distclean()
    
    prepareDirs()

    del sys.argv[1:]
    sys.argv.extend(wafCmdLine)
    Build.BuildContext.execute = assist.autoconfigure(Build.BuildContext.execute)
    cwd = assist.BUILDROOT
    Scripting.waf_entry_point(cwd, Context.WAFVERSION, WAF_DIR)

    return 0
