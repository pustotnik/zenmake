# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module implements a different way to run/use Waf
"""

import os
import sys
import traceback
from waflib import Options, Context, Errors
from zm import WAF_DIR
#from zm.constants import BUILDCONF_FILENAMES
from zm import log, utils, wscriptimpl, assist

joinpath = os.path.join

#def _loadPathsFromLockfile(dirpath):
#
#    from waflib.ConfigSet import ConfigSet
#    env = ConfigSet()
#    try:
#        env.load(joinpath(dirpath, Options.lockfile))
#        ino = os.stat(dirpath)[stat.ST_INO]
#    except EnvironmentError:
#        return
#
#    import stat
#    from waflib import Utils
#    # check if the folder was not moved
#    for _dir in (env.run_dir, env.top_dir, env.out_dir):
#        if not _dir:
#            continue
#        if Utils.is_win32:
#            if dirpath == _dir:
#                load = True
#                break
#        else:
#            # if the filesystem features symlinks, compare the inode numbers
#            try:
#                ino2 = os.stat(_dir)[stat.ST_INO]
#            except OSError:
#                pass
#            else:
#                if ino == ino2:
#                    load = True
#                    break
#    else:
#        log.warn('invalid lock file in %s', dirpath)
#        load = False
#
#    if load:
#        Context.run_dir = env.run_dir
#        Context.top_dir = env.top_dir
#        Context.out_dir = env.out_dir

def _prepareBuildDir(bconfPaths):
    """
    Prepare some paths for correct work
    """

    buildroot     = bconfPaths.buildroot
    realbuildroot = bconfPaths.realbuildroot
    if not os.path.exists(realbuildroot):
        os.makedirs(realbuildroot)
    if buildroot != realbuildroot and not os.path.exists(buildroot):
        utils.mksymlink(realbuildroot, buildroot)

def _setWafMainModule(bconfdir, bconfname):
    """
    Alternative implementation of Scripting.set_main_module
    """

    # ZenMake uses only one 'wscript' and it is the wscriptimpl module
    Context.g_module = wscriptimpl

    # Set path to the buildconf file
    Context.g_module.root_path = joinpath(bconfdir, bconfname)

def _setupWafOptions(wafCmdLine):
    del sys.argv[1:]
    sys.argv.extend(wafCmdLine)

    ctx = Context.create_context('options')
    ctx.execute()
    assert Options.commands

def runCommand(bconfHandler, cmdName):
    """
    Executes a single Waf command.
    """
    ctx = Context.create_context(cmdName)
    ctx.log_timer = utils.Timer()
    ctx.options = Options.options # provided for convenience
    ctx.cmd = cmdName
    setattr(ctx, 'bconfHandler', bconfHandler)

    try:
        ctx.execute()
    finally:
        # WAF issue 1374
        ctx.finalize()
    return ctx

def setupAndRunCommands(wafCmdLine, bconfHandler):
    """
	Execute the Waf commands that were given on the command-line, and the other options
	"""

    def runNextCmd():
        cmdName = Options.commands.pop(0)
        ctx = runCommand(bconfHandler, cmdName)
        log.info('%r finished successfully (%s)', cmdName, ctx.log_timer)

    assist.setWscriptVars(wscriptimpl, bconfHandler)

    _setupWafOptions(wafCmdLine)
    runCommand(bconfHandler, 'init')
    if Options.commands[0] == 'distclean':
        runNextCmd()
    if Options.commands:
        _prepareBuildDir(bconfHandler.confPaths)
    while Options.commands:
        runNextCmd()

    runCommand(bconfHandler, 'shutdown')

def run(cmd, wafCmdLine, bconfHandler):
    """
    Replacement for the Scripting.waf_entry_point
    """

    #TODO: Is Context.run_dir necessary? In waf it's a dir where wscript is.
    # I made it as dir where top-level buildconf is located

    bconfPaths = bconfHandler.confPaths

    # Store current directory before any chdir
    Context.waf_dir = WAF_DIR
    Context.run_dir = Context.launch_dir = bconfPaths.buildconfdir
    Context.out_dir = bconfPaths.buildout

    # ZenMake doesn't use lockfile in a project root

    #startdir = bconfPaths.buildconfdir
    #try:
    #    dirfiles = os.listdir(startdir)
    #except OSError:
    #    dirfiles = []
    #    log.error('Directory %r is unreadable!', startdir)

    #if Options.lockfile in dirfiles:
    #    _loadPathsFromLockfile(startdir)

    #if not Context.run_dir:
    #    if any(x in dirfiles for x in BUILDCONF_FILENAMES):
    #        Context.run_dir = startdir

    try:
        os.chdir(Context.run_dir)
    except OSError:
        log.error('The folder %r is unreadable', Context.run_dir)
        sys.exit(1)

    _setWafMainModule(bconfPaths.buildconfdir, bconfPaths.buildconffile)
    verbose = cmd.args.verbose

    #pylint: disable=broad-except
    try:
        setupAndRunCommands(wafCmdLine, bconfHandler)
    except Errors.WafError as ex:
        if verbose > 1:
            log.pprint('RED', ex.verbose_msg)
        log.error(ex.msg)
        sys.exit(1)
    except Exception:
        traceback.print_exc(file = sys.stdout)
        sys.exit(2)
    except KeyboardInterrupt:
        log.pprint('RED', 'Interrupted')
        sys.exit(68)
    #pylint: enable=broad-except
