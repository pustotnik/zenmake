# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import subprocess

from waflib import Options, Context, Configure, Utils
from waflib.ConfigSet import ConfigSet
from zm.constants import BUILDCONF_FILENAMES
from zm import log, assist, utils, error, wscriptimpl
from zm.pyutils import stringtype
from zm.pypkg import PkgPath
from zm.waf import launcher

joinpath = os.path.join

# Force to turn off internal WAF autoconfigure decorator.
# It's just to rid of needless work and to save working time.
Configure.autoconfig = False

def _isBuildTypeNotConfigured(bconfHandler):

    from zm.buildconf.utils import gatherAllTaskNames

    buildtype = bconfHandler.selectedBuildType
    zmcachedir = bconfHandler.confPaths.zmcachedir

    allTaskNames = gatherAllTaskNames(bconfHandler.conf)
    for taskName in allTaskNames:
        taskVariant = assist.makeTaskVariantName(buildtype, taskName)
        fname = assist.makeCacheConfFileName(zmcachedir, taskVariant)
        if not os.path.exists(fname):
            return True
    return False

def _loadLockfileEnv(bconfPaths):
    env = ConfigSet()
    try:
        env.load(joinpath(bconfPaths.wscriptout, Options.lockfile))
    except EnvironmentError:
        return None
    return env

def _handleNoLockInTop(ctx, envGetter):

    if Context.top_dir and Context.out_dir:
        return False

    env = envGetter()
    if not env:
        if ctx.cmd != 'build':
            return True
        from zm.error import ZenMakeError
        raise ZenMakeError('The project was not configured: run "configure" '
                           'first or enable features.autoconfig in buildconf !')

    Context.run_dir = env.run_dir
    Context.top_dir = env.top_dir
    Context.out_dir = env.out_dir

    # It's needed to rerun command to apply changes in Context otherwise
    # Waf won't work correctly.
    launcher.runCommand(ctx.bconfHandler, ctx.cmd)
    return True

def wrapBldCtxNoLockInTop(method):
    """
    Decorator that handles only case with conf.env.NO_LOCK_IN_RUN = True and/or
    conf.env.NO_LOCK_IN_TOP = True
    """

    def execute(ctx):
        bconfPaths = ctx.bconfHandler.confPaths
        if not _handleNoLockInTop(ctx, lambda: _loadLockfileEnv(bconfPaths)):
            method(ctx)

    return execute

def wrapBldCtxAutoConf(method):
    """
    Decorator that enables context commands to run *configure* as needed.
    It handles also case with conf.env.NO_LOCK_IN_RUN = True and/or
    conf.env.NO_LOCK_IN_TOP = True
    """

    def runConfigAndCommand(ctx, env):
        launcher.runCommand(ctx.bconfHandler, env.config_cmd or 'configure')
        launcher.runCommand(ctx.bconfHandler, ctx.cmd)

    def execute(ctx):

        wrapBldCtxAutoConf.callCounter += 1
        if wrapBldCtxAutoConf.callCounter > 10:
            # I some cases due to programming error, user actions or system
            # problems we can get infinite call of current function. Maybe
            # later I'll think up better protection but in normal case
            # it shouldn't happen.
            raise Exception('Infinite recursion was detected')

        if wrapBldCtxAutoConf.onlyRunMethod:
            method(ctx)
            # reset flag
            wrapBldCtxAutoConf.onlyRunMethod = False
            return

        bconfPaths = ctx.bconfHandler.confPaths

        # Execute the configuration automatically
        autoconfig = ctx.bconfHandler.conf.features['autoconfig']

        if not autoconfig:
            if not _handleNoLockInTop(ctx, lambda: _loadLockfileEnv(bconfPaths)):
                method(ctx)
            return

        # mark for the next recursive call
        # FIXME: can be more stable solution?
        wrapBldCtxAutoConf.onlyRunMethod = True

        env = _loadLockfileEnv(bconfPaths)
        if not env:
            log.warn('Configuring the project')
            runConfigAndCommand(ctx, ConfigSet())
            return

        if env.run_dir != bconfPaths.buildconfdir:
            runConfigAndCommand(ctx, env)
            return

        cmnConfSet = assist.loadZenMakeCmnConfSet(bconfPaths)
        if not cmnConfSet or assist.isZmVersionChanged(cmnConfSet) or \
                    assist.areMonitoredFilesChanged(cmnConfSet) or \
                    assist.areToolchainEnvVarsAreChanged(cmnConfSet):
            runConfigAndCommand(ctx, env)
            return

        if _isBuildTypeNotConfigured(ctx.bconfHandler):
            runConfigAndCommand(ctx, env)
            return

        if not _handleNoLockInTop(ctx, lambda: env):
            method(ctx)
        return

    return execute

wrapBldCtxAutoConf.callCounter = 0
wrapBldCtxAutoConf.onlyRunMethod = False

def wrapUtilsGetProcess(_):
    """
    Wrap Utils.get_process to have possibility of running from a zip package.
    """

    from zm import WAF_DIR
    filepath = joinpath(WAF_DIR, 'waflib', 'processor.py')
    # it must be text
    code = PkgPath(filepath).readText()

    def execute():
        if Utils.process_pool:
            return Utils.process_pool.pop()

        cmd = [sys.executable, '-c', code]
        return subprocess.Popen(cmd, stdout = subprocess.PIPE,
                                stdin = subprocess.PIPE, bufsize = 0)

    return execute

def getFileExtensions(src):
    """
    Returns the file extensions for the list of files given as input

    :param src: files to process
    :list src: list of string or :py:class:`waflib.Node.Node`
    :return: list of file extensions
    :rtype: set of strings
	"""

    # This implementation gives more optimal result for using in
    # waflib.Tools.c_aliases.sniff_features

    ret = set()
    for path in utils.toList(src):
        if not isinstance(path, stringtype):
            path = path.name
        ret.add(path[path.rfind('.') + 1:])
    return ret

def wrapCtxRecurse():
    """
    Wrap Context.Context.recurse to work correctly without 'wscript'.
    """

    #pylint: disable=too-many-arguments,unused-argument
    def execute(ctx, dirs, name = None, mandatory = True, once = True, encoding = None):

        try:
            cache = ctx.recurseCache
        except AttributeError:
            cache = ctx.recurseCache = {}

        for dirpath in utils.toList(dirs):

            if not os.path.isabs(dirpath):
                # absolute paths only
                dirpath = joinpath(ctx.path.abspath(), dirpath)

            # try to find buildconf
            for fname in BUILDCONF_FILENAMES:
                node = ctx.root.find_node(joinpath(dirpath, fname))
                if node:
                    break
            else:
                continue

            tup = (node, name or ctx.fun)
            if once and tup in cache:
                continue

            cache[tup] = True
            ctx.pre_recurse(node)
            try:
                # try to find function for command
                func = getattr(wscriptimpl, (name or ctx.fun), None)
                if not func:
                    if not mandatory:
                        continue
                    errmsg = 'No function %r defined in %s' % \
                                (name or ctx.fun, wscriptimpl.__file__)
                    raise error.ZenMakeError(errmsg)
                # call function for command
                func(ctx)
            finally:
                ctx.post_recurse(node)

    return execute

def wrapCfgCtxPostRecurse():
    """
    Wrap Configure.ConfigurationContext.post_recurse to avoid some actions.
    It's mostly for performance
    """

    def execute(ctx, node):
        super(Configure.ConfigurationContext, ctx).post_recurse(node)
        ctx.hash = 0
        ctx.files = []

    return execute

def setupAll():
    """ Setup all wrappers for Waf """

    Utils.get_process = wrapUtilsGetProcess(Utils.get_process)

    Context.Context.recurse = wrapCtxRecurse()
    Configure.ConfigurationContext.post_recurse = wrapCfgCtxPostRecurse()

    from waflib import Build

    Build.BuildContext.execute = wrapBldCtxAutoConf(Build.BuildContext.execute)
    for ctxCls in (Build.CleanContext, Build.ListContext):
        ctxCls.execute = wrapBldCtxNoLockInTop(ctxCls.execute)

    from waflib.Tools import c_aliases
    c_aliases.get_extensions = getFileExtensions
