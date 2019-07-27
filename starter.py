#!/usr/bin/env python
# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import atexit
if sys.hexversion < 0x2070000:
    raise ImportError('Python >= 2.7 is required')

joinpath = os.path.join

SCRIPTS_ROOTDIR = os.path.dirname(os.path.abspath(__file__))

WAF_DIR = joinpath(SCRIPTS_ROOTDIR, 'waf')
ZM_DIR = joinpath(SCRIPTS_ROOTDIR, 'zm')
AUX_DIR = joinpath(SCRIPTS_ROOTDIR, 'auxiliary')

sys.path.insert(1, WAF_DIR)
# argparse from the https://pypi.org/project/argparse/ supports alieses
#sys.path.insert(1, AUX_DIR)

#pylint: disable=wrong-import-position
from waflib import Context
from zm.constants import WSCRIPT_NAME
Context.WSCRIPT_FILE = WSCRIPT_NAME

def atExit():
    """
    Callback function for atexit
    """

    from zm import shared
    if not shared.buildConfHandler:
        return
    wscriptfile = shared.buildConfHandler.confPaths.wscriptfile
    if os.path.isfile(wscriptfile):
        os.remove(wscriptfile)

atexit.register(atExit)

def prepareDirs(bconfPaths):
    """
    Prepare some paths for correct work
    """
    from zm import utils

    if not os.path.exists(bconfPaths.buildroot):
        os.makedirs(bconfPaths.buildroot)
    if bconfPaths.buildsymlink and not os.path.exists(bconfPaths.buildsymlink):
        utils.mksymlink(bconfPaths.buildroot, bconfPaths.buildsymlink)

    # We regard ZM_DIR as a directory where file 'wscript' is located.
    # Creating of symlink is cheaper than copying of file but on Windows OS
    # there are some problems with using of symlinks.
    from shutil import copyfile
    copyfile(joinpath(ZM_DIR, 'wscript'), bconfPaths.wscriptfile)

def handleCLI(buildConfHandler, args, buildOnEmpty):
    """
    Handle CLI and return command object and waf cmd line
    """
    from zm import cli

    defaults = dict(
        buildtype = buildConfHandler.defaultBuildType
    )

    cmd, wafCmdLine = cli.parseAll(args, defaults, buildOnEmpty)
    cli.selected = cmd
    return cmd, wafCmdLine

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
    from waflib import Scripting, Build

    from zm import log, assist, shared
    from zm.buildconf import loader as bconfloader
    from zm.buildconf.handler import BuildConfHandler

    buildconf = bconfloader.load(check = False)
    if assist.isBuildConfChanged(buildconf):
        bconfloader.validate(buildconf)
    buildConfHandler = BuildConfHandler(buildconf)
    shared.buildConfHandler = buildConfHandler
    bconfPaths = buildConfHandler.confPaths
    isBuildConfFake = assist.isBuildConfFake(buildconf)

    cmd, wafCmdLine = handleCLI(buildConfHandler, sys.argv, not isBuildConfFake)

    if isBuildConfFake:
        log.error('Config buildconf.py not found. Check buildconf.py '
                  'exists in the project directory.')
        sys.exit(1)

    # Special case for 'distclean'
    if cmd.name == 'distclean':
        assist.distclean(bconfPaths)
        return 0

    if cmd.args.distclean:
        assist.distclean(bconfPaths)

    prepareDirs(bconfPaths)

    del sys.argv[1:]
    sys.argv.extend(wafCmdLine)
    from zm.wafwrappers import wrapBldCtxNoLockInTop, wrapBldCtxAutoConf
    Build.BuildContext.execute = wrapBldCtxAutoConf(cmd, buildConfHandler,
                                                    Build.BuildContext.execute)
    for ctxCls in (Build.CleanContext, Build.ListContext):
        ctxCls.execute = wrapBldCtxNoLockInTop(buildConfHandler, ctxCls.execute)

    cwd = bconfPaths.wscriptdir
    Scripting.waf_entry_point(cwd, Context.WAFVERSION, WAF_DIR)

    return 0
