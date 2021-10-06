# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import subprocess

from waflib import Context, Configure, Utils
from zm.constants import PYTHON_EXE
from zm.autodict import AutoDict
from zm.utils import envValToBool
from zm.pypkg import PkgPath
from zm.waf import assist, launcher, configure

joinpath = os.path.join

# Force to turn off internal WAF autoconfigure decorator.
# It's just to rid of needless work and to save working time.
Configure.autoconfig = False

_autoconfStates = {}

def _handleNoLockInTop(ctx, zmMetaGetter):

    if Context.top_dir and Context.out_dir:
        return False

    zmMeta = zmMetaGetter()
    if not zmMeta:
        if ctx.cmd != 'build':
            return True
        from zm.error import ZenMakeError
        raise ZenMakeError('The project was not configured: run "configure" '
                           'first or enable general.autoconfig in buildconf !')

    Context.run_dir = zmMeta.rundir
    Context.top_dir = zmMeta.topdir
    Context.out_dir = zmMeta.outdir

    # It's needed to rerun command to apply changes in Context otherwise
    # Waf won't work correctly.
    # TODO: try to find a way without rerun of command
    launcher.runCommand(ctx.bconfManager, ctx.cmd)
    return True

def wrapBldCtxNoLockInTop(method):
    """
    Decorator that handles only case with conf.env.NO_LOCK_IN_RUN = True and/or
    conf.env.NO_LOCK_IN_TOP = True
    """

    def execute(ctx):
        if not _handleNoLockInTop(ctx, ctx.zmMetaConf):
            method(ctx)

    return execute

def wrapCmdCtxAutoConf(method):
    """
    Decorator that enables context commands to run *configure* as needed.
    It handles also case with conf.env.NO_LOCK_IN_RUN = True and/or
    conf.env.NO_LOCK_IN_TOP = True
    """

    def runConfigAndCommand(ctx):
        if ctx.cmd == 'configure':
            method(ctx)
        else:
            launcher.runCommand(ctx.bconfManager, 'configure')
            launcher.runCommand(ctx.bconfManager, ctx.cmd)

    def execute(ctx):

        zmcmd = ctx.cmd

        from zm import cli
        cliargs = cli.selected.args
        if zmcmd == 'configure' and cliargs.force:
            method(ctx)
            return

        autoconfState = _autoconfStates.setdefault(zmcmd, AutoDict(
            callCounter = 0,
            onlyRunMethod = False
        ))

        autoconfState.callCounter += 1
        if autoconfState.callCounter > 10:
            # I some cases due to programming error, user actions or system
            # problems we can get infinite call of current function. Maybe
            # later I'll think up better protection but in normal case
            # it shouldn't happen.
            raise Exception('Infinite recursion was detected')

        if autoconfState.onlyRunMethod:
            method(ctx)
            # reset flag
            autoconfState.onlyRunMethod = False
            return

        bconf = ctx.bconfManager.root

        # Execute the configuration automatically
        autoconfig = os.environ.get('ZENMAKE_AUTOCONFIG', '')
        if autoconfig:
            autoconfig = envValToBool(autoconfig)
        else:
            autoconfig = bconf.general['autoconfig']

        if not autoconfig:
            if zmcmd == 'configure' or not _handleNoLockInTop(ctx, ctx.zmMetaConf):
                method(ctx)
            return

        # mark for the next recursive call
        # FIXME: can be more stable solution?
        autoconfState.onlyRunMethod = True

        zmMeta = ctx.zmMetaConf()
        if not zmMeta:
            runConfigAndCommand(ctx)
            return

        bconfPaths = bconf.confPaths
        rootdir    = bconfPaths.rootdir
        zmcachedir = bconfPaths.zmcachedir
        buildtype  = bconf.selectedBuildType
        if assist.needToConfigure(zmMeta, rootdir, zmcachedir, buildtype, cliargs):
            runConfigAndCommand(ctx)
            return

        if zmcmd != 'configure' and not _handleNoLockInTop(ctx, lambda: zmMeta):
            method(ctx)
        return

    return execute

def wrapUtilsGetProcess(_):
    """
    Wrap Utils.get_process to make it possible to run from a zip package.
    """

    from zm import WAF_DIR
    filepath = joinpath(WAF_DIR, 'waflib', 'processor.py')
    # it must be text
    code = PkgPath(filepath).readText()

    def execute():
        if Utils.process_pool:
            return Utils.process_pool.pop()

        # pylint: disable = consider-using-with
        cmd = [PYTHON_EXE, '-c', code]
        return subprocess.Popen(cmd, stdout = subprocess.PIPE,
                                stdin = subprocess.PIPE, bufsize = 0)

    return execute

def setUp():
    """ Set up some wrappers for Waf """

    Utils.get_process = wrapUtilsGetProcess(Utils.get_process)

    from waflib import Build

    for ctxCls in (configure.ConfigurationContext, Build.BuildContext):
        ctxCls.execute = wrapCmdCtxAutoConf(ctxCls.execute)
    for ctxCls in (Build.CleanContext, Build.ListContext):
        ctxCls.execute = wrapBldCtxNoLockInTop(ctxCls.execute)

setUp()
