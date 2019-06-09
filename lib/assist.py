# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD, see LICENSE for more details.
"""

import sys, os
import collections
from waflib import Context, Options, Configure, Build, Utils, Logs
from waflib.ConfigSet import ConfigSet
from utils import unfoldPath

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3

if PY3:
    string_types = str
else:
    string_types = basestring

joinpath  = os.path.join
abspath   = os.path.abspath
realpath  = os.path.realpath

# Avoid writing .pyc files
sys.dont_write_bytecode = True
import buildconf
sys.dont_write_bytecode = False

# Execute the configuration automatically
autoconfig = buildconf.features.get('autoconfig', True)

# Force to turn off internal WAF autoconfigure decorator.
# It's just to rid of needless work and to save working time.
Configure.autoconfig = False

# List of all waf commands. It's used for correct work of distclean command
wafcommands = []

WSCRIPT_FILE     = joinpath(os.path.dirname(realpath(__file__)), 'wscript')
BUILDCONF_FILE   = abspath(buildconf.__file__)
BUILDCONF_DIR    = os.path.dirname(BUILDCONF_FILE)
PROJECTNAME      = buildconf.project['name']
BUILDROOT        = unfoldPath(BUILDCONF_DIR, buildconf.buildroot)
BUILDSYMLINK     = unfoldPath(BUILDCONF_DIR, getattr(buildconf, 'buildsymlink', None))
BUILDOUT         = joinpath(BUILDROOT, 'out')
PROJECTROOT      = unfoldPath(BUILDCONF_DIR, buildconf.project['root'])
SRCROOT          = unfoldPath(BUILDCONF_DIR, buildconf.srcroot)
SRCSYMLINKNAME   = '%s-%s' %(os.path.basename(PROJECTROOT), os.path.basename(SRCROOT))
SRCSYMLINK       = joinpath(BUILDROOT, SRCSYMLINKNAME)
WAFCACHEDIR      = joinpath(BUILDOUT, Build.CACHE_DIR)
WAFCACHEFILE     = joinpath(WAFCACHEDIR, Build.CACHE_SUFFIX)

RAVENCACHEDIR    = WAFCACHEDIR
RAVENCACHESUFFIX = '.raven.py'
RAVENCMNFILE     = joinpath(BUILDOUT, '.raven-common')

def dumpRavenCommonFile():
    ravenCmn = ConfigSet()
    # Firstly I had added WSCRIPT_FILE in this list but then realized that it's not necessary
    # because wscript don't have any project settings
    ravenCmn.monitfiles = [BUILDCONF_FILE]
    ravenCmn.monithash  = 0

    for file in ravenCmn.monitfiles:
        ravenCmn.monithash = Utils.h_list((ravenCmn.monithash, Utils.readf(file, 'rb')))
    ravenCmn.store(RAVENCMNFILE)

def loadTasksFromCache():
    """
    Load cheched tasks from config cache it exists
    """
    result = {}
    try:
        oldenv = ConfigSet()
        oldenv.load(WAFCACHEFILE)
        if 'alltasks' in oldenv:
            result = oldenv.alltasks
    except EnvironmentError:
        pass
    return result

def makeTargetPath(ctx, dirName, targetName):
    #return joinpath(targetName)
    return joinpath(ctx.out_dir, dirName, targetName)

def makeCacheConfFileName(name):
    return joinpath(RAVENCACHEDIR, name + RAVENCACHESUFFIX)

def getTaskVariantName(buildtype, taskName):
    return '%s.%s' % (buildtype, taskName)

def copyEnv(env):
    
    from copy import deepcopy

    newenv = ConfigSet()
    # deepcopy only current table whithout parents
    newenv.table = deepcopy(env.table)
    parent = getattr(env, 'parent', None)
    if parent:
        newenv.parent = parent
    return newenv

def deepcopyEnv(env):
    # Function deepcopy doesn't work with ConfigSet and ConfigSet.detach doesn't make deepcopy 
    # for already detached objects (WAF version is 2.0.15).
    
    from copy import deepcopy

    newenv = ConfigSet()
    # keys() returns all keys from current env and all parents
    for k in env.keys():
        newenv[k] = deepcopy(env[k])
    return newenv

def setTaskEnvVars(env, taskParams):

    SAME_TYPE_PARAMS = ('cflags', 'cxxflags', 'cppflags', 'linkflags', 'defines')

    for p in SAME_TYPE_PARAMS:
        val = taskParams.get(p, None)
        if val:
            env[p.upper()] = val.split()

    # set variables from env
    ENV_VARS = ('CFLAGS', 'CXXFLAGS', 'LDFLAGS')
    for var in ENV_VARS:
        if var in os.environ:
            # FIXME: should we add or replace?
            # env is a copy-on-write dict so we should force write operation
            current = env[var] # it returns [] if key is not exists
            env[var] = current + os.environ[var].split()

def handleTaskIncludesParam(taskParams):
    # From wafbook:
    # Includes paths are given relative to the directory containing the wscript file.
    # Providing absolute paths are best avoided as they are a source of portability problems.
    includes = taskParams.get('includes', None)
    if includes:
        if isinstance(includes, string_types):
            includes = includes.split()
        includes = [ x if os.path.isabs(x) else \
            joinpath(SRCSYMLINKNAME, x) for x in includes ]
    return includes

def fullclean():

    import shutil

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

    # It's not necessary to define something for built-in toolchains
    # but format is:
    # toolchains = {
    #     'g++': {
    #         # here you can set/override env vars like 'CXX', 'LINK_CXX', ...
    #         'CXX'     : 'g++',
    #     },
    # }
    toolchains = {}

    def __init__(self, conf):
        self._origin = conf
        self._ready  = {}

        self._ready['tasks']      = {}
        self._ready['toolchains'] = {}

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

    def toolchainNames(self, buildtype):
        buildtype = self.realBuildType(buildtype)
        if buildtype in self._ready['toolchains']:
            return self._ready['toolchains'][buildtype]

        toolchains = set()
        tasks = self.tasks(buildtype)
        for taskParams in tasks.values():
            c = taskParams.get('toolchain', None)
            if c:
                toolchains.add(c)

        toolchains = tuple(toolchains)
        self._ready['toolchains'][buildtype] = toolchains
        return toolchains

def autoconfigure(method):
    """
    Decorator that enables context commands to run *configure* as needed.
    Alternative version.
    """

    def areFilesChanged():
        ravenCmn = ConfigSet()
        try:
            ravenCmn.load(RAVENCMNFILE)
        except EnvironmentError:
            return True

        h = 0
        for f in ravenCmn.monitfiles:
            try:
                h = Utils.h_list((h, Utils.readf(f, 'rb')))
            except EnvironmentError:
                return True
        
        return h != ravenCmn.monithash

    def areBuildtypesNotConfigured():
        buildtypes = Options.options.buildtype
        if isinstance(buildtypes, string_types):
            buildtypes = [buildtypes]

        for buildtype in buildtypes:
            for taskName in buildconf.tasks.keys():
                taskVariant = getTaskVariantName(buildtype, taskName)
                fname = makeCacheConfFileName(taskVariant)
                if not os.path.exists(fname):
                    return True
        return False

    def runconfig(self, env):
        from waflib import Scripting
        Scripting.run_command(env.config_cmd or 'configure')
        Scripting.run_command(self.cmd)

    def execute(self):

        if not autoconfig:
            return method(self)

        autoconfigure.callCounter += 1
        if autoconfigure.callCounter > 2:
            # I some cases due to programming error, user actions or system problems we can get 
            # infinite call of current function. Maybe later I'll think up better protection
            # but in normal case it shouldn't happen.
            raise Exception('Infinite recursion was detected')

        env = ConfigSet()
        try:
            env.load(joinpath(Context.out_dir, Options.lockfile))
        except EnvironmentError:
            Logs.warn('Configuring the project')
            return runconfig(self, env)
        
        if env.run_dir != Context.run_dir:
            return runconfig(self, env)

        if areFilesChanged():
            return runconfig(self, env)

        if areBuildtypesNotConfigured():
            return runconfig(self, env)

        return method(self)

    return execute

autoconfigure.callCounter = 0