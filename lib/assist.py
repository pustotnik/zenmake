# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD, see LICENSE for more details.
"""

import sys, os
import collections
import shutil
from waflib import Options, Configure, Logs
from utils import unfoldPath

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3

if PY3:
    string_types = str
else:
    string_types = basestring

joinpath  = os.path.join
abspath   = os.path.abspath

# Avoid writing .pyc files
sys.dont_write_bytecode = True
import buildconf
sys.dont_write_bytecode = False

wafcommands = []

BUILDCONF_DIR  = os.path.dirname(abspath(buildconf.__file__))
PROJECTNAME    = buildconf.project['name']
BUILDROOT      = unfoldPath(BUILDCONF_DIR, buildconf.buildroot)
BUILDSYMLINK   = unfoldPath(BUILDCONF_DIR, getattr(buildconf, 'buildsymlink', None))
PROJECTROOT    = unfoldPath(BUILDCONF_DIR, buildconf.project['root'])
SRCROOT        = unfoldPath(BUILDCONF_DIR, buildconf.srcroot)
SRCSYMLINKNAME = '%s-%s' %(os.path.basename(PROJECTROOT), os.path.basename(SRCROOT))
SRCSYMLINK     = joinpath(BUILDROOT, SRCSYMLINKNAME)

def useBuldconfInAutoconfig(cfgCtx):

    from waflib import Utils

    # It's hack for correct working of WAF feature 'autoconfig' when build params are not in wscript.
    # I didn't manage to find more clear solution.
    # It's not necessary for regular use of WAF where wscript files are config files for WAF.
    # It's also not neccessary if you don't use feature 'autoconfig' but I think that 'autoconfig'
    # is very useful. So I made this.
    buildconfPath = abspath(buildconf.__file__)
    cfgCtx.hash = Utils.h_list((cfgCtx.hash, Utils.readf(buildconfPath, 'rb')))
    cfgCtx.files.append(buildconfPath)

def setTaskEnvVars(env, taskParams):

    SAME_TYPE_PARAMS = ('cflags', 'cxxflags', 'cppflags', 'linkflags', 'defines')

    for p in SAME_TYPE_PARAMS:
        val = taskParams.get(p, None)
        if val:
            env[p.upper()] = val.split()

def fullclean():

    if BUILDSYMLINK and os.path.isdir(BUILDSYMLINK) and os.path.exists(BUILDSYMLINK):
        Logs.info("Removing directory '%s'" % BUILDSYMLINK)
        shutil.rmtree(BUILDSYMLINK, ignore_errors = True)

    if BUILDSYMLINK and os.path.islink(BUILDSYMLINK) and os.path.lexists(BUILDSYMLINK):
        Logs.info("Removing symlink '%s'" % BUILDSYMLINK)
        os.remove(BUILDSYMLINK)

    if os.path.exists(BUILDROOT):
        REALBUILDROOT = os.path.realpath(BUILDROOT)
        Logs.info("Removing directory '%s'" % REALBUILDROOT)
        shutil.rmtree(REALBUILDROOT, ignore_errors = True)

        if os.path.islink(BUILDROOT) and os.path.lexists(BUILDROOT):
            Logs.info("Removing symlink '%s'" % BUILDROOT)
            os.remove(BUILDROOT)

    lockfile = os.path.join(PROJECTROOT, Options.lockfile)
    if os.path.exists(lockfile):
        Logs.info("Removing lockfile '%s'" % lockfile)
        os.remove(lockfile)

    lockfile = os.path.join(PROJECTROOT, 'waf', Options.lockfile)
    if os.path.exists(lockfile):
        Logs.info("Removing lockfile '%s'" % lockfile)
        os.remove(lockfile)

class BuildConfParser(object):

    def __init__(self, conf):
        self._origin = conf
        self._ready  = {}

        self._ready['tasks']     = {}
        self._ready['compilers'] = {}

    def defaultBuildType(self):
        return self._origin.buildtypes.get('default', '')

    def buildTypes(self):
        if 'build-types' in self._ready:
            return self._ready['build-types']

        buildtypes = set(self._origin.buildtypes.keys())
        if 'default' in buildtypes:
            buildtypes.remove('default')
        buildtypes = list(buildtypes)
        self._ready['build-types'] = buildtypes
        return buildtypes

    def realBuildType(self, buildtype):

        if 'build-types-map' not in self._ready:
            btMap = dict()
            buildtypes = self._origin.buildtypes
            for bt, val in buildtypes.items():
                btVal = val
                btKey = bt
                while not isinstance(btVal, collections.Mapping):
                    if not isinstance(btVal, string_types):
                        raise ValueError("Invalid type of buildtype value '%s'" % type(btVal))
                    btKey = btVal
                    if btKey not in buildtypes:
                        raise ValueError("Build type '%s' was not found" % btKey)
                    btVal = buildtypes[btKey]
                    if btKey == bt and btVal == val:
                        raise ValueError("Circular reference was found")


                btMap[bt] = btKey

            self._ready['build-types-map'] = btMap

        btMap = self._ready['build-types-map']
        if buildtype not in btMap:
            raise ValueError("Build type '%s' was not found" % buildtype)

        return btMap[buildtype]

    def tasks(self, buildtype):
        buildtype = self.realBuildType(buildtype)
        if buildtype in self._ready['tasks']:
            return self._ready['tasks'][buildtype]

        tasks = {}

        #knownBuildTypeParams = ('compiler', 'cflags',
        #    'cxxflags', 'linkflags', 'defines', 'env' )
        #knownTaskParams = ( 'features', 'source', 'target', 'includes',
        #    'sys-libs', 'ver-num', 'use', 'sys-lib-path') + knownBuildTypeParams

        for taskName, taskParams in self._origin.tasks.items():
            task = {}
            tasks[taskName] = task

            # 1. Copy exising params of selected buildtype from 'buildtypes'
            task.update(self._origin.buildtypes[buildtype])

            # 2. Copy/replace existing params from origin task
            task.update(taskParams)
            if 'buildtypes' in task:
                del task['buildtypes']
            # 3. Copy/replace exising params of selected buildtype from 'tasks'
            taskBuildTypes = taskParams.get('buildtypes', None)
            if not taskBuildTypes:
                continue
            taskBuildParams = taskBuildTypes.get(buildtype, dict())
            task.update(taskBuildParams)

        self._ready['tasks'][buildtype] = tasks
        return tasks

    def compilers(self, buildtype):
        buildtype = self.realBuildType(buildtype)
        if buildtype in self._ready['compilers']:
            return self._ready['compilers'][buildtype]

        compilers = set()
        tasks = self.tasks(buildtype)
        for taskParams in tasks.values():
            c = taskParams.get('compiler', None)
            if c:
                compilers.add(c)

        compilers = tuple(compilers)
        self._ready['compilers'][buildtype] = compilers
        return compilers

def autoconfigure(method):
    """
    Decorator that enables context commands to run *configure* as needed.
    """
    def execute(self):

        if not Configure.autoconfig:
            return method(self)

        #print(self.variant)
        #print(self.env.alltasks)
        return method(self)

    return execute
