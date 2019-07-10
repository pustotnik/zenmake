# coding=utf-8
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
import zm.buildconfutil
import zm.utils
from zm.utils import stringtypes, maptype
import zm.toolchains as toolchains
from zm.autodict import AutoDict

joinpath = os.path.join
abspath  = os.path.abspath
realpath = os.path.realpath

buildconf = zm.buildconfutil.loadConf()

# Execute the configuration automatically
autoconfig = buildconf.features['autoconfig']

# Force to turn off internal WAF autoconfigure decorator.
# It's just to rid of needless work and to save working time.
Configure.autoconfig = False

PROJECT_NAME     = buildconf.project['name']
PROJECT_VERSION  = buildconf.project['version']

PLATFORM         = zm.utils.platform()
WSCRIPT_FILE     = joinpath(os.path.dirname(realpath(__file__)), 'wscript')
BUILDCONF_FILE   = abspath(buildconf.__file__)
BUILDCONF_DIR    = os.path.dirname(BUILDCONF_FILE)
BUILDROOT        = zm.utils.unfoldPath(BUILDCONF_DIR, buildconf.buildroot)
BUILDSYMLINK     = zm.utils.unfoldPath(BUILDCONF_DIR, buildconf.buildsymlink)
BUILDOUT         = joinpath(BUILDROOT, 'out')
PROJECTROOT      = zm.utils.unfoldPath(BUILDCONF_DIR, buildconf.project['root'])
SRCROOT          = zm.utils.unfoldPath(BUILDCONF_DIR, buildconf.srcroot)
WAFCACHEDIR      = joinpath(BUILDOUT, Build.CACHE_DIR)
WAFCACHEFILE     = joinpath(WAFCACHEDIR, Build.CACHE_SUFFIX)

ZENMAKECACHEDIR    = WAFCACHEDIR
ZENMAKECACHESUFFIX = '.zenmake.py'
ZENMAKECMNFILE     = joinpath(BUILDOUT, '.zenmake-common')

def dumpZenMakeCommonFile():
    
    zmCmn = ConfigSet()
    # Firstly I had added WSCRIPT_FILE in this list but then realized that 
    # it's not necessary because wscript don't have any project settings 
    # in our case.
    zmCmn.monitfiles = [BUILDCONF_FILE]
    zmCmn.monithash  = 0

    for file in zmCmn.monitfiles:
        zmCmn.monithash = Utils.h_list((zmCmn.monithash, 
                                            Utils.readf(file, 'rb')))
    zmCmn.store(ZENMAKECMNFILE)

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
    return joinpath(ZENMAKECACHEDIR, name + ZENMAKECACHESUFFIX)

def getTaskVariantName(buildtype, taskName):
    return '%s.%s' % (buildtype, taskName)

def copyEnv(env):

    newenv = ConfigSet()
    # deepcopy only current table whithout parents
    newenv.table = deepcopy(env.table)
    parent = getattr(env, 'parent', None)
    if parent:
        newenv.parent = parent
    return newenv

def deepcopyEnv(env):
    # Function deepcopy doesn't work with ConfigSet and ConfigSet.detach 
    # doesn't make deepcopy for already detached objects 
    # (WAF version is 2.0.15).

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

def runConfTests(cfgCtx, buildtype, taskParams):
    
    confTests = taskParams.get('conftests', [])
    for entity in confTests:
        act = entity.pop('act', None)
        if act == 'check-sys-libs':
            sysLibs = Utils.to_list(taskParams.get('sys-libs', []))
            kwargs = entity
            for lib in sysLibs:
                kwargs['lib'] = lib
                cfgCtx.check(**kwargs)
        elif act == 'check-headers':
            headers = Utils.to_list(entity.pop('names', []))
            kwargs = entity
            for header in headers:
                kwargs['header_name'] = header
                cfgCtx.check(**kwargs)
        elif act == 'check-libs':
            libs = Utils.to_list(entity.pop('names', []))
            autodefine = entity.pop('autodefine', False)
            kwargs = entity
            for lib in libs:
                kwargs['lib'] = lib
                if autodefine:
                    kwargs['define_name'] = 'HAVE_LIB_' + lib.upper()
                cfgCtx.check(**kwargs)
        elif act == 'check':
            cfgCtx.check(**entity)
        elif act == 'write-config-header':
            fileName = entity.pop('file', '%s_%s' % 
                                    (taskParams['name'].lower(), 'config.h'))
            fileName = joinpath(buildtype, fileName)
            entity['guard'] = entity.pop('guard',
                                        Utils.quote_define_name(PROJECT_NAME + '_' + fileName))
            cfgCtx.write_config_header(fileName, **entity)
        else:
            cfgCtx.fatal('unknown act %r for conftests in task %r!' % 
                                        (act, taskParams['name']))  

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

    if not buildconfHandler.toolchainNames:
        Logs.warn("WARN: No toolchains found. Is buildconf correct?")
    
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
    # Includes paths are given relative to the directory containing the 
    # wscript file. Providing absolute paths are best avoided as they are 
    # a source of portability problems.
    includes = taskParams.get('includes', [])
    if includes:
        if isinstance(includes, stringtypes):
            includes = includes.split()
        includes = [ x if os.path.isabs(x) else \
            joinpath(SRCROOT, x) for x in includes ]
    # The includes='.' add the build directory path. It's needed to use config
    # header with 'conftests'.
    includes.append('.')
    return includes

def fullclean():
    """
    It does almost the same thing as distclean from waf. But distclean can 
    not remove directory with file wscript or symlink to it if distclean 
    was called from that wscript.
    """

    import shutil
    import zm.cli
    verbose = 1
    if zm.cli.selected:
        verbose = zm.cli.selected.args.verbose

    if BUILDSYMLINK and os.path.isdir(BUILDSYMLINK) and os.path.exists(BUILDSYMLINK):
        if verbose >= 1:
            Logs.info("Removing directory '%s'" % BUILDSYMLINK)
        shutil.rmtree(BUILDSYMLINK, ignore_errors = True)

    if BUILDSYMLINK and os.path.islink(BUILDSYMLINK) and os.path.lexists(BUILDSYMLINK):
        if verbose >= 1:
            Logs.info("Removing symlink '%s'" % BUILDSYMLINK)
        os.remove(BUILDSYMLINK)

    if os.path.exists(BUILDROOT):
        REALBUILDROOT = os.path.realpath(BUILDROOT)
        if verbose >= 1:
            Logs.info("Removing directory '%s'" % REALBUILDROOT)
        shutil.rmtree(REALBUILDROOT, ignore_errors = True)

        if os.path.islink(BUILDROOT) and os.path.lexists(BUILDROOT):
            if verbose >= 1:
                Logs.info("Removing symlink '%s'" % BUILDROOT)
            os.remove(BUILDROOT)

    lockfile = os.path.join(PROJECTROOT, Options.lockfile)
    if os.path.exists(lockfile):
        if verbose >= 1:
            Logs.info("Removing lockfile '%s'" % lockfile)
        os.remove(lockfile)

    lockfile = os.path.join(PROJECTROOT, 'waf', Options.lockfile)
    if os.path.exists(lockfile):
        if verbose >= 1:
            Logs.info("Removing lockfile '%s'" % lockfile)
        os.remove(lockfile)

def distclean():

    """
    Full replacement for distclean from WAF
    """

    cmdTimer = Utils.Timer()

    import zm.cli as cli
    if cli.selected:
        colors = {'yes' : 2, 'auto' : 1, 'no' : 0}[cli.selected.args.color]
        Logs.enable_colors(colors)

    fullclean()

    Logs.info('%r finished successfully (%s)', 'distclean', cmdTimer)

def isBuildConfFake():
    return isinstance(buildconf.tasks, stringtypes)

def _getBuildTypeFromCLI():
    import zm.cli as cli
    if not cli.selected or not cli.selected.args.buildtype:
        return ''
    return cli.selected.args.buildtype

class BuildConfHandler(object):

    def __init__(self, conf = buildconf):

        self.cmdLineHandled = False

        self._origin = conf
        self._platforms = self._origin.platforms

        self._meta = AutoDict()
        # just in case
        self._meta.buildtypes = AutoDict()

        self._preprocess()

    def _preprocess(self):

        # NOTICE: this method should not have any heavy operations 

        allBuildTypes = set(self._origin.buildtypes.keys())
        if 'default' in allBuildTypes:
            allBuildTypes.remove('default')
        self._meta.buildtypes.allnames = allBuildTypes

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
                while not isinstance(btVal, maptype):
                    if not isinstance(btVal, stringtypes):
                        raise WafError("Invalid type of buildtype value '%s'" 
                                        % type(btVal))
                    btKey = btVal
                    if btKey not in buildtypes:
                        raise WafError("Build type '%s' was not found, check "
                                        "your config." % btKey)
                    btVal = buildtypes[btKey]
                    if btKey == bt and btVal == val:
                        raise WafError("Circular reference was found")

                btMap[bt] = btKey

            self._meta.buildtypes.map = btMap

        bt = self._meta.buildtypes.map.get(buildtype, False)
        if not bt:
            raise WafError("Build type '%s' was not found, check "
                            "your config." % buildtype)

        return bt

    def handleCmdLineArgs(self):

        if self.cmdLineHandled:
            return

        if isBuildConfFake():
            raise WafError('Config buildconf.py not found. Check buildconf.py '
                            'exists in the project directory.')

        buildtype = _getBuildTypeFromCLI()

        supportedBuildTypes = self.supportedBuildTypes
        if buildtype not in supportedBuildTypes:
            raise WafError("Invalid choice for build type: '%s', "
                "(choose from %s)" % 
                (buildtype, str(supportedBuildTypes)[1:-1]))

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
            raise WafError("Default build type '%s' was not found, "
                            "check your config." % buildtype)
        
        self._meta.buildtypes.default = buildtype
        return buildtype

    @property
    def selectedBuildType(self):
        if not self.cmdLineHandled:
            raise Exception("Command line args wasn't handled yet")

        return self._meta.buildtypes.selected

    @property
    def supportedBuildTypes(self):

        if 'supported' in self._meta.buildtypes:
            return self._meta.buildtypes.supported

        # handle 'buildconf.platforms'
        if PLATFORM in self._platforms:
            validBuildTypes = self._platforms[PLATFORM].get('valid', [])
            if not validBuildTypes:
                raise WafError("No valid build types for platform '%s' "
                                "in config" % PLATFORM)
            for bt in validBuildTypes:
                if bt not in self._origin.buildtypes:
                    raise WafError("Build type '%s' for platform '%s' "
                        "was not found, check your config." % (bt, PLATFORM))
            self._meta.buildtypes.supported = validBuildTypes
        else:
            self._meta.buildtypes.supported = list(self._meta.buildtypes.allnames)
        
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

        if 'names' in self._meta.toolchains:
            return self._meta.toolchains.names

        # gather unique names
        toolchains = set()
        for taskParams in self.tasks.values():
            c = taskParams.get('toolchain', None)
            if c:
                toolchains.add(c)

        toolchains = tuple(toolchains)
        self._meta.toolchains.names = toolchains
        return toolchains

    @property
    def customToolchains(self):

        if 'custom' in self._meta.toolchains:
            return self._meta.toolchains.custom

        srcToolchains = self._origin.toolchains
        customToolchains = AutoDict()
        for name, info in srcToolchains.items():
            vars = deepcopy(info) # don't change origin
            kind = vars.pop('kind', None)
            if kind is None:
                raise WafError("Toolchain '%s': field 'kind' not found" % name)
            
            for k, v in vars.items():
                # try to identify path and do nothing in another case 
                path = zm.utils.unfoldPath(PROJECTROOT, v)
                if os.path.exists(path):
                    vars[k] = path

            customToolchains[name].kind = kind
            customToolchains[name].vars = vars
                    
        self._meta.toolchains.custom = customToolchains
        return customToolchains

"""
Singleton instance of BuildConfHandler for possibility using of already 
calculated data in different modules 
"""
buildConfHandler = BuildConfHandler()

def autoconfigure(method):
    """
    Decorator that enables context commands to run *configure* as needed.
    Alternative version.
    """

    def areFilesChanged():
        zmCmn = ConfigSet()
        try:
            zmCmn.load(ZENMAKECMNFILE)
        except EnvironmentError:
            return True

        h = 0
        for f in zmCmn.monitfiles:
            try:
                h = Utils.h_list((h, Utils.readf(f, 'rb')))
            except EnvironmentError:
                return True
        
        return h != zmCmn.monithash

    def areBuildTypesNotConfigured():
        buildtype = _getBuildTypeFromCLI()
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
            # I some cases due to programming error, user actions or system 
            # problems we can get infinite call of current function. Maybe 
            # later I'll think up better protection but in normal case 
            # it shouldn't happen.
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