#!/usr/bin/env python
# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
if sys.hexversion < 0x2070000:
    raise ImportError('Python >= 2.7 is required')

joinpath = os.path.join

SCRIPTS_ROOTDIR = os.path.dirname(os.path.abspath(__file__))

WAF_DIR = joinpath(SCRIPTS_ROOTDIR, 'waf')
ZM_DIR = joinpath(SCRIPTS_ROOTDIR, 'zm')
ARGPARSE_DIR = joinpath(SCRIPTS_ROOTDIR, 'argparse')

sys.path.insert(1, WAF_DIR)
# argparse from the https://pypi.org/project/argparse/ supports alieses
sys.path.insert(1, ARGPARSE_DIR)

def main():
    """
    Prepare and start Waf with ZenMake stuffs
    """

    # When set to a non-empty value, the process will not search for a build
    # configuration in upper folders.
    os.environ['NOCLIMB'] = '1'

    # use of Options.lockfile is not enough
    os.environ['WAFLOCK'] = '.lock-wafbuild'
    from waflib import Options
    Options.lockfile = '.lock-wafbuild'
    from waflib import Scripting, Context, Build, Logs

    import zm.assist
    import zm.utils
    import zm.cli

    def prepareDirs():
        if not os.path.exists(zm.assist.BUILDROOT):
            os.makedirs(zm.assist.BUILDROOT)
        if zm.assist.BUILDSYMLINK and not os.path.exists(zm.assist.BUILDSYMLINK):
            zm.utils.mksymlink(zm.assist.BUILDROOT, zm.assist.BUILDSYMLINK)

        # We regard ZM_DIR as a directory where file 'wscript' is located.
        # Creating of symlink is cheaper than copying of file but on Windows OS
        # there are some problems with using of symlinks.
        from shutil import copyfile
        copyfile(joinpath(ZM_DIR, 'wscript'),
                 joinpath(zm.assist.BUILDROOT, 'wscript'))

    wafCmdLine = zm.cli.parseAll(sys.argv)

    if zm.assist.isBuildConfFake():
        Logs.error('Config buildconf.py not found. Check buildconf.py '
                   'exists in the project directory.')
        sys.exit(1)

    # Special case for 'distclean'
    cmd = zm.cli.selected
    if cmd.name == 'distclean':
        zm.assist.distclean()
        return 0

    if cmd.args.distclean:
        zm.assist.distclean()

    prepareDirs()

    del sys.argv[1:]
    sys.argv.extend(wafCmdLine)
    Build.BuildContext.execute = zm.assist.autoconfigure(Build.BuildContext.execute)
    cwd = zm.assist.BUILDROOT
    Scripting.waf_entry_point(cwd, Context.WAFVERSION, WAF_DIR)

    return 0
