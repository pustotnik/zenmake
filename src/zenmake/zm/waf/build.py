# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys

from waflib.ConfigSet import ConfigSet
from waflib.Build import BuildContext as WafBuildContext
from zm.constants import DEFAULT_BUILDWORKNAME
from zm.pyutils import viewvalues
from zm.utils import asmethod, Timer
from zm import log, db, error
from zm.waf.assist import makeTasksCachePath
from zm.deps import produceExternalDeps

joinpath = os.path.join

BuildContext = WafBuildContext

# WafBuildContext is used for many other waf commands as the base class
# and so to insert new methods into this class the decorator @asmethod is used.

@asmethod(WafBuildContext, '__init__', wrap = True, callOrigFirst = True)
def _ctxInit(self, **kwargs):
    # pylint: disable = unused-argument

    self.buildWorkDirName = DEFAULT_BUILDWORKNAME
    if self.bconfManager:
        bconfFeatures = self.bconfManager.root.features
        buildWorkDirName = bconfFeatures.get('build-work-dir-name')
        if buildWorkDirName is not None:
            self.buildWorkDirName = buildWorkDirName

@asmethod(WafBuildContext, 'load_envs', wrap = True, callOrigFirst = True)
def _loadEnvs(self):
    self.loadTasks()

def _loadTasksDataForClean(self, bconf, cachePath):
    zmMetaConf = self.zmMetaConf()
    if not zmMetaConf:
        raise error.ZenMakeError("Project has not been configured")

    try:
        zmMetaConfAttrs = zmMetaConf.attrs
        lastPyVer = zmMetaConfAttrs['last-python-ver']
        lastPyVer = lastPyVer.split('.')[0]
        lastDbFormat = zmMetaConfAttrs['last-dbformat']
    except AttributeError:
        zmmetafile = bconf.confPaths.zmmetafile
        raise error.ZenMakeError("Invalid format of file %r" % zmmetafile)

    curPyVer = str(sys.version_info[0])

    if lastDbFormat == 'pickle' and lastPyVer != curPyVer:
        msg = "ZenMake does not support using of python 2 and 3"
        msg += " at the same time on the same projects."
        msg += " Run 'distclean' or 'configure'"
        raise error.ZenMakeError(msg)

    tasksDb = db.factory(cachePath, lastDbFormat)
    if not tasksDb.exists():
        buildtype = bconf.selectedBuildType
        log.info("Buildtype '%s' not found. Nothing to clean" % buildtype)
        return None

    return tasksDb.load()

@asmethod(WafBuildContext, 'loadTasks')
def _loadTasks(self):

    bconf = self.bconfManager.root
    buildtype = bconf.selectedBuildType
    cachedir = bconf.confPaths.zmcachedir
    cachePath = makeTasksCachePath(cachedir, buildtype)

    self.zmtasks = {}
    self.zmdepconfs = {}

    if self.cmd == 'clean':
        tasksData = _loadTasksDataForClean(self, bconf, cachePath)
        if not tasksData:
            return
    else:
        if not db.exists(cachePath):
            self.fatal("Buildtype '%s' not found! Was step 'configure' missed?"
                       % buildtype)

        tasksData = db.loadFrom(cachePath)

    self.zmtasks = tasks = tasksData['tasks']
    taskenvs = tasksData['taskenvs']

    rootenv = self.all_envs['']
    for taskParams in viewvalues(tasks):
        taskVariant = taskParams['$task.variant']
        env = ConfigSet()
        env.table = taskenvs[taskVariant]
        env.parent = rootenv
        self.all_envs[taskVariant] = env

    self.zmdepconfs = tasksData['depconfs']

@asmethod(WafBuildContext, 'init_dirs', wrap = True, callOrigFirst = True)
def _initDirs(self):
    blddir = self.variant_dir
    if self.buildWorkDirName:
        blddir = joinpath(blddir, self.buildWorkDirName)
        self.bldnode = self.root.make_node(blddir)
        self.bldnode.mkdir()

@asmethod(WafBuildContext, 'execute_build')
def _executeBuild(self):

    if self.cmd in ('build', 'install', 'uninstall'):
        produceExternalDeps(self)
        log.printStep(self.cmd.capitalize() + 'ing')

    self.recurse([self.run_dir])

    # display the time elapsed in the progress bar
    self.timer = Timer()

    try:
        self.compile()
    finally:
        if self.progress_bar == 1 and sys.stderr.isatty():
            colors = log.colors
            prgsState = self.producer.processed or 1
            msg = self.progress_line(prgsState, prgsState, colors.BLUE, colors.NORMAL)
            logExtra = {
                'stream': sys.stderr,
                'c1': colors.cursor_off,
                'c2': colors.cursor_on,
            }
            log.info(msg, extra = logExtra)

    try:
        self.producer.bld = None
        del self.producer
    except AttributeError:
        pass

@asmethod(WafBuildContext, 'validateVariant')
def _validateVariant(self):
    """ Check current variant and return it """

    if self.variant is None:
        self.fatal('No variant!')

    buildtype = self.variant
    return buildtype
