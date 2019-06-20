# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
import collections
from copy import deepcopy
from waflib import Context, Options, Configure, Build, Utils, Logs
from waflib.ConfigSet import ConfigSet
from waflib.Errors import WafError
import utils
from utils import string_types
import toolchains
from autodict import AutoDict

joinpath  = os.path.join
abspath   = os.path.abspath
realpath  = os.path.realpath

buildconf = utils.loadPyModule('buildconf')

# Execute the configuration automatically
autoconfig = buildconf.features.get('autoconfig', True)

# Force to turn off internal WAF autoconfigure decorator.
# It's just to rid of needless work and to save working time.
Configure.autoconfig = False

# List of all waf commands. It's used for correct work of distclean command
wafcommands = []

PROJECT_NAME     = buildconf.project['name']
PROJECT_VERSION  = buildconf.project['version']

PLATFORM         = utils.platform()
WSCRIPT_FILE     = joinpath(os.path.dirname(realpath(__file__)), 'wscript')
BUILDCONF_FILE   = abspath(buildconf.__file__)
BUILDCONF_DIR    = os.path.dirname(BUILDCONF_FILE)
BUILDROOT        = utils.unfoldPath(BUILDCONF_DIR, buildconf.buildroot)
BUILDSYMLINK     = utils.unfoldPath(BUILDCONF_DIR, getattr(buildconf, 'buildsymlink', None))
BUILDOUT         = joinpath(BUILDROOT, 'out')
PROJECTROOT      = utils.unfoldPath(BUILDCONF_DIR, buildconf.project['root'])
SRCROOT          = utils.unfoldPath(BUILDCONF_DIR, buildconf.srcroot)
#SRCSYMLINKNAME   = '%s-%s' %(os.path.basename(PROJECTROOT), os.path.basename(SRCROOT))
SRCSYMLINKNAME   = os.path.basename(PROJECTROOT)
SRCSYMLINK       = joinpath(BUILDROOT, SRCSYMLINKNAME)
WAFCACHEDIR      = joinpath(BUILDOUT, Build.CACHE_DIR)
WAFCACHEFILE     = joinpath(WAFCACHEDIR, Build.CACHE_SUFFIX)

RAVENCACHEDIR    = WAFCACHEDIR
RAVENCACHESUFFIX = '.raven.py'
RAVENCMNFILE     = joinpath(BUILDOUT, '.raven-common')

def dumpRavenCommonFile():
    
    ravenCmn = ConfigSet()
    # Firstly I had added WSCRIPT_FILE in this list but then realized that it's not necessary
    # because wscript don't have any project settings in our case.
    ravenCmn.monitfiles = [BUILDCONF_FILE]
    ravenCmn.monithash  = 0

    for file in ravenCmn.monitfiles:
        ravenCmn.monithash = Utils.h_list((ravenCmn.monithash, Utils.readf(file, 'rb')))
    ravenCmn.store(RAVENCMNFILE)

def loadTasksFromCache():
    """
    Load cached tasks from config cache if it exists
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

def getBuildTypeFromCLI():
    return Options.options.buildtype

def copyEnv(env):

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

    newenv = ConfigSet()
    # keys() returns all keys from current env and all parents
    for k in env.keys():
        newenv[k] = deepcopy(env[k])
    return newenv

def setTaskEnvVars(env, taskParams):

    cfgEnvVars = toolchains.CompilersInfo.allCfgEnvVars()
    for var in cfgEnvVars:
        val = taskParams.get(var.lower(), None)
        if val:
            env[var] = Utils.to_list(val)

def loadDetectedCompiler(cfgCtx, kind):

    # without 'auto-'
    _kind = kind[5:]
    
    compilers = toolchains.CompilersInfo.compilers(_kind)
    envVar    = toolchains.CompilersInfo.varToSetCompiler(_kind)

    for compiler in compilers:
        cfgCtx.env.stash()
        cfgCtx.start_msg('Checking for %r' % compiler)
        try:
            cfgCtx.load(compiler)
        except cfgCtx.errors.ConfigurationError:
            cfgCtx.env.revert()
            cfgCtx.end_msg(False)
        else:
            if cfgCtx.env[envVar]:
                cfgCtx.end_msg(cfgCtx.env.get_flat(envVar))
                cfgCtx.env.commit()
                break
            cfgCtx.env.revert()
            cfgCtx.end_msg(False)
    else:
        cfgCtx.fatal('could not configure a %s compiler!' % _kind.upper())

def loadToolchains(cfgCtx, buildconfHandler, copyFromEnv):
    
    toolchainsEnv = {}
    oldEnvName = cfgCtx.variant

    def loadToolchain(toolchain):
        toolname = toolchain
        if toolname in toolchainsEnv:
            return
        cfgCtx.setenv(toolname, env = copyFromEnv)
        custom  = buildconfHandler.customToolchains.get(toolname, None)
        if custom is not None:
            for var, val in custom.vars.items():
                cfgCtx.env[var] = val
            toolchain = custom.kind
        
        if toolchain.startswith('auto-'):
            loadDetectedCompiler(cfgCtx, toolchain)
        else:
            cfgCtx.load(toolchain)
        toolchainsEnv[toolname] = cfgCtx.env

    for toolchain in buildconfHandler.toolchainNames:
        loadToolchain(toolchain)        

    # switch to old env due to calls of 'loadToolchain'
    cfgCtx.setenv(oldEnvName)

    return toolchainsEnv

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
    """
    It does almost the same thing as distclean from waf. But distclean can not remove 
    directory with file wscript or symlink to it if dictclean was called from that wscript.
    """

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

class BuildConfHandler(object):

    def __init__(self, conf = buildconf):

        self.cmdLineHandled = False

        self._origin = conf
        self._platforms  = getattr(self._origin, 'platforms', {})

        self._meta  = AutoDict()
        # just in case
        self._meta.buildtypes = AutoDict()

        self._preprocess()

    def _preprocess(self):
        allBuildTypes = set(self._origin.buildtypes.keys())
        if 'default' in allBuildTypes:
            allBuildTypes.remove('default')
        self._meta.buildtypes.allnames = allBuildTypes

        # handle 'buildconf.platforms'
        if PLATFORM in self._platforms:
            validBuildTypes = self._platforms[PLATFORM].get('valid', [])
            if not validBuildTypes:
                raise WafError("No valid build types for platform '%s' in config" % PLATFORM)
            for bt in validBuildTypes:
                if bt not in self._origin.buildtypes:
                    raise WafError("Build type '%s' for platform '%s' "
                        "was not found, check your config." % (bt, PLATFORM))
            self._meta.buildtypes.supported = validBuildTypes
        else:
            self._meta.buildtypes.supported = list(allBuildTypes)

        # handle 'buildconf.toolchains'
        srcToolchains = getattr(self._origin, 'toolchains', {})
        customToolchains = AutoDict()
        for name, info in srcToolchains.items():
            vars = deepcopy(info) # don't change origin
            kind = vars.pop('kind', None)
            if kind is None:
                raise WafError("Toolchain '%s': field 'kind' not found" % name)
            
            for k, v in vars.items():
                # try to identify path and do nothing in another case 
                path = utils.unfoldPath(BUILDCONF_DIR, v)
                if os.path.exists(path):
                    vars[k] = path

            customToolchains[name].kind = kind
            customToolchains[name].vars = vars
                    
        self._meta.toolchains.custom = customToolchains

    def _handleTasksEnvVars(self, tasks):

        cinfo = toolchains.CompilersInfo
        FLAG_VARS      = cinfo.allFlagVars()
        TOOLCHAIN_VARS = cinfo.allVarsToSetCompiler()

        for taskParams in tasks.values():
            # handle flags
            for var in FLAG_VARS:
                envVal = os.environ.get(var, None)
                if not envVal:
                    continue

                paramName = var.lower()
                
                current = taskParams.get(paramName, [])
                current = Utils.to_list(current)
                # FIXME: should we add or replace?
                taskParams[paramName] = current + Utils.to_list(envVal)

            # handle toolchains
            for var in TOOLCHAIN_VARS:
                toolchain = os.environ.get(var, None)
                if not toolchain:
                    continue
                if var.lower() in taskParams.get('features', ''):
                    taskParams['toolchain'] = toolchain

    def _getRealBuildType(self, buildtype):

        if 'map' not in self._meta.buildtypes:
            btMap = dict()
            buildtypes = self._origin.buildtypes
            for bt, val in buildtypes.items():
                btVal = val
                btKey = bt
                while not isinstance(btVal, collections.Mapping):
                    if not isinstance(btVal, string_types):
                        raise WafError("Invalid type of buildtype value '%s'" % type(btVal))
                    btKey = btVal
                    if btKey not in buildtypes:
                        raise WafError("Build type '%s' was not found, check your config." % btKey)
                    btVal = buildtypes[btKey]
                    if btKey == bt and btVal == val:
                        raise WafError("Circular reference was found")


                btMap[bt] = btKey

            self._meta.buildtypes.map = btMap

        bt = self._meta.buildtypes.map.get(buildtype, False)
        if not bt:
            raise WafError("Build type '%s' was not found, check your config." % buildtype)

        return bt

    def handleCmdLineArgs(self):

        buildtype = getBuildTypeFromCLI()

        if buildtype not in self._meta.buildtypes.supported:
            raise WafError("Invalid choice for build type: '%s', (choose from %s)" 
                % (buildtype, str(self._meta.buildtypes.supported)[1:-1]))

        self._meta.buildtypes.selected = self._getRealBuildType(buildtype)

        self.cmdLineHandled = True

    @property
    def defaultBuildType(self):
        if 'default' in self._meta.buildtypes:
            return self._meta.buildtypes.default

        buildtype = self._origin.buildtypes.get('default', '')
        if PLATFORM in self._platforms:
            buildtype = self._platforms[PLATFORM].get('default', '')
        if buildtype == 'default' or not buildtype:
            buildtype = ''
        elif buildtype not in self._origin.buildtypes:
            raise WafError("Default build type '%s' was not found, check your config." % buildtype)
        
        self._meta.buildtypes.default = buildtype
        return buildtype

    @property
    def selectedBuildType(self):
        if not self.cmdLineHandled:
            raise Exception("Command line args wasn't handled yet")

        return self._meta.buildtypes.selected

    @property
    def supportedBuildTypes(self):
        return self._meta.buildtypes.supported

    @property
    def tasks(self):
        buildtype = self.selectedBuildType
        if buildtype in self._meta.tasks:
            return self._meta.tasks[buildtype]

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

        self._handleTasksEnvVars(tasks)

        self._meta.tasks[buildtype] = tasks
        return tasks

    @property
    def toolchainNames(self):

        if 'allnames' in self._meta.toolchains:
            return self._meta.toolchains.names

        # gather unique names
        toolchains = set()
        for taskParams in self.tasks.values():
            c = taskParams.get('toolchain', None)
            if c:
                toolchains.add(c)

        toolchains = tuple(toolchains)
        self._meta.toolchains.allnames = toolchains
        return toolchains

    @property
    def customToolchains(self):
        return self._meta.toolchains.custom

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

    def areBuildTypesNotConfigured():
        buildtype = getBuildTypeFromCLI()
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
        if autoconfigure.callCounter > 10:
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

        if areBuildTypesNotConfigured():
            return runconfig(self, env)

        return method(self)

    return execute

autoconfigure.callCounter = 0