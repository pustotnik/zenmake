# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some portions derived from Thomas Nagy's Waf code
 Waf is Copyright (c) 2005-2019 Thomas Nagy

 This module implements a different way to run/use Waf
"""

import os
import sys
import traceback
from waflib import Options, Context, Errors
from zm import WAF_DIR
from zm.constants import WAF_LOCKFILE
from zm.pyutils import viewvalues
from zm import log, utils, cli
from zm.error import ZenMakeConfError
from zm.waf import wscriptimpl, assist
from zm.waf.options import setupOptionVerbose

# pylint: disable = unused-import
# These modules must be just imported
from zm.waf import context, configure, build, install
# pylint: enable = unused-import

joinpath = os.path.join

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

def _setWafMainModule(rootdir):
    """
    Alternative implementation of Scripting.set_main_module
    """

    # ZenMake uses only one 'wscript' and it is the wscriptimpl module
    Context.g_module = wscriptimpl

    # Set root path
    fakename = 'fakeconfname'
    Context.g_module.root_path = joinpath(rootdir, fakename)

def _prepareAndLoadFeatures(bconfManager):

    from zm.features import loadFeatures

    ctx = Context.Context()
    setattr(ctx, 'bconfManager', bconfManager)

    try:
        # process all actual features from buildconf(s)
        for bconf in bconfManager.configs:
            for taskParams in viewvalues(bconf.tasks):
                assist.detectTaskFeatures(ctx, taskParams)
                assist.validateTaskFeatures(taskParams)
    except ZenMakeConfError as ex:
        origMsg = ex.msg
        ex.msg = "Error in the file %r:" % bconf.path
        for line in origMsg.splitlines():
            ex.msg += "\n  %s" % line
        raise ex

    # load modules for all actual features from buildconf(s)
    loadFeatures(bconfManager)

def setWscriptVars(module, bconf):
    """
    Set wscript vars: top, out, APPNAME, VERSION
    """
    module.top = bconf.confPaths.wscripttop
    module.out = bconf.confPaths.wscriptout
    module.APPNAME = bconf.projectName
    module.VERSION = bconf.projectVersion

def setupWafOptions(bconfManager, wafCmdLine):
    """
    Execure 'options' as the Waf command.
    This command parses command line args for the Waf.
    """

    del sys.argv[1:]
    sys.argv.extend(wafCmdLine)

    ctx = Context.create_context('options')

    # inject zenmake vars
    setattr(ctx, 'bconfManager', bconfManager)

    ctx.execute()
    assert Options.commands

def runCommand(bconfManager, cmdName):
    """
    Executes a single Waf command.
    """

    cliArgs = cli.selected.args

    verbose = None
    if cmdName == 'configure':
        verbose = cliArgs.get('verboseConfigure')
    elif cmdName == 'build':
        verbose = cliArgs.get('verboseBuild')
    if verbose is None:
        verbose = cliArgs.verbose

    if Options.options.verbose != verbose:
        Options.options.verbose = verbose
        setupOptionVerbose(Options.options)

    ctx = Context.create_context(cmdName)
    ctx.log_timer = utils.Timer()
    ctx.options = Options.options # provided for convenience
    ctx.cmd = cmdName

    # inject zenmake vars
    setattr(ctx, 'bconfManager', bconfManager)

    try:
        ctx.execute()
    finally:
        # WAF issue 1374
        ctx.finalize()
    return ctx

def setupAndRunCommands(wafCmdLine, bconfManager):
    """
	Execute the Waf commands that were given on the command-line, and the other options
	"""

    def runNextCmd():
        cmdName = Options.commands.pop(0)
        ctx = runCommand(bconfManager, cmdName)
        log.info('%r finished successfully (%s)', cmdName, ctx.log_timer)

    bconf = bconfManager.root
    setWscriptVars(wscriptimpl, bconf)

    setupWafOptions(bconfManager, wafCmdLine)

    runCommand(bconfManager, 'init')
    if Options.commands[0] == 'distclean':
        runNextCmd()
    if Options.commands:
        _prepareBuildDir(bconf.confPaths)
    while Options.commands:
        runNextCmd()

    runCommand(bconfManager, 'shutdown')

def run(cwd, cmd, wafCmdLine, bconfManager):
    """
    Replacement for the Scripting.waf_entry_point
    """

    # pylint: disable = unused-import
    # load and set waf wrappers
    from zm.waf import wrappers
    # pylint: enable = unused-import

    bconf = bconfManager.root
    bconfPaths = bconf.confPaths

    # use of Options.lockfile is not enough
    os.environ['WAFLOCK'] = WAF_LOCKFILE
    Options.lockfile = WAF_LOCKFILE

    # note: ZenMake doesn't use Waf lockfile in a project dir, only in a buildout dir

    # Store current directory before any chdir
    Context.waf_dir = WAF_DIR

    # bconfPaths.startdir == bconf.rootdir if bconf == bconfManager.root
    rootdir = bconf.rootdir
    Context.launch_dir = rootdir
    Context.run_dir    = rootdir
    Context.out_dir    = bconfPaths.buildout

    try:
        os.chdir(Context.run_dir)
    except OSError:
        log.error('The folder %r is unreadable', Context.run_dir)
        sys.exit(1)

    _setWafMainModule(bconf.rootdir)

    cliArgs = cmd.args
    verbose = cliArgs.verbose

    # pylint: disable = broad-except
    try:

        if 'buildtype' in cliArgs:
            assist.initBuildType(bconfManager, cliArgs.buildtype)
            _prepareAndLoadFeatures(bconfManager)

        setupAndRunCommands(wafCmdLine, bconfManager)
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
