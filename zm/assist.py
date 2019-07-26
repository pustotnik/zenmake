# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 There are functions and classes specific to process with our wscript.
"""

import os
from copy import deepcopy
from waflib.ConfigSet import ConfigSet
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm import utils, toolchains, log
from zm.autodict import AutoDict
from zm.error import ZenMakeError, ZenMakeLogicError
from zm.constants import WAF_CACHE_DIRNAME, WAF_CACHE_NAMESUFFIX, \
                         ZENMAKE_CACHE_NAMESUFFIX, ZENMAKE_COMMON_FILENAME, \
                         PLATFORM, BUILDOUTNAME, WSCRIPT_NAME

joinpath = os.path.join

def dumpZenMakeCommonFile(bconfPaths):
    """
    Dump file ZENMAKE_COMMON_FILENAME with some things like monitored
    for changes files.
    """

    zmCmn = ConfigSet()
    # Firstly I had added WSCRIPT_FILE in this list but then realized that
    # it's not necessary because wscript don't have any project settings
    # in our case.
    zmCmn.monitfiles = [bconfPaths.buildconffile]
    zmCmn.monithash  = 0

    for file in zmCmn.monitfiles:
        zmCmn.monithash = utils.mkHashOfStrings((zmCmn.monithash,
                                                 utils.readFile(file, 'rb')))
    zmCmn.store(bconfPaths.zmcmnfile)

def loadTasksFromCache(cachefile):
    """
    Load cached tasks from config cache if it exists
    """
    result = {}
    try:
        oldenv = ConfigSet()
        oldenv.load(cachefile)
        if 'alltasks' in oldenv:
            result = oldenv.alltasks
    except EnvironmentError:
        pass
    return result

def makeTargetPath(ctx, dirName, targetName):
    """ Compose path for target that is used in build task"""
    return joinpath(ctx.out_dir, dirName, targetName)

def makeCacheConfFileName(zmcachedir, name):
    """ Make file name of specific zenmake cache config file"""
    return joinpath(zmcachedir, name + ZENMAKE_CACHE_NAMESUFFIX)

def getTaskVariantName(buildtype, taskName):
    """ Get 'variant' for task by fixed template"""
    return '%s.%s' % (buildtype, taskName)

def copyEnv(env):
    """
    Make shallow copy of ConfigSet object
    """

    newenv = ConfigSet()
    # deepcopy only current table whithout parents
    newenv.table = deepcopy(env.table)
    parent = getattr(env, 'parent', None)
    if parent:
        newenv.parent = parent
    return newenv

def deepcopyEnv(env):
    """
    Make deep copy of ConfigSet object

    Function deepcopy doesn't work with ConfigSet and ConfigSet.detach
    doesn't make deepcopy for already detached objects
    (WAF version is 2.0.15).
    """

    newenv = ConfigSet()
    # keys() returns all keys from current env and all parents
    for k in env.keys():
        newenv[k] = deepcopy(env[k])
    return newenv

def setTaskEnvVars(env, taskParams):
    """
    Set up some env vars for build task such as compiler flags
    """

    cfgEnvVars = toolchains.CompilersInfo.allCfgEnvVars()
    for var in cfgEnvVars:
        val = taskParams.get(var.lower(), None)
        if val:
            env[var] = utils.toList(val)

def runConfTests(cfgCtx, buildtype, taskParams):
    """
    Run supported configuration tests/checks
    """

    confTests = taskParams.get('conftests', [])
    for entity in confTests:
        act = entity.pop('act', None)
        if act == 'check-sys-libs':
            sysLibs = utils.toList(taskParams.get('sys-libs', []))
            kwargs = entity
            for lib in sysLibs:
                kwargs['lib'] = lib
                cfgCtx.check(**kwargs)
        elif act == 'check-headers':
            headers = utils.toList(entity.pop('names', []))
            kwargs = entity
            for header in headers:
                kwargs['header_name'] = header
                cfgCtx.check(**kwargs)
        elif act == 'check-libs':
            libs = utils.toList(entity.pop('names', []))
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
            projectName = cfgCtx.env['PROJECT_NAME'] or ''
            guardname = utils.quoteDefineName(projectName + '_' + fileName)
            entity['guard'] = entity.pop('guard', guardname)
            cfgCtx.write_config_header(fileName, **entity)
        else:
            cfgCtx.fatal('unknown act %r for conftests in task %r!' %
                         (act, taskParams['name']))

def loadDetectedCompiler(cfgCtx, kind):
    """
    Load auto detected compiler by its kind
    """

    # without 'auto-'
    lang = kind[5:]

    compilers = toolchains.CompilersInfo.compilers(lang)
    envVar    = toolchains.CompilersInfo.varToSetCompiler(lang)

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
        cfgCtx.fatal('could not configure a %s compiler!' % lang.upper())

def loadToolchains(cfgCtx, buildconfHandler, copyFromEnv):
    """
    Load all selected toolchains in cfgCtx
    """

    if not buildconfHandler.toolchainNames:
        log.warn("WARN: No toolchains found. Is buildconf correct?")

    toolchainsEnv = {}
    oldEnvName = cfgCtx.variant

    def loadToolchain(toolchain):
        toolname = toolchain
        if toolname in toolchainsEnv:
            return
        cfgCtx.setenv(toolname, env = copyFromEnv)
        custom  = buildconfHandler.customToolchains.get(toolname, None)
        if custom is not None:
            for var, val in viewitems(custom.vars):
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

def handleTaskIncludesParam(taskParams, srcroot):
    """
    Get valid 'includes' for build task
    """

    # From wafbook:
    # Includes paths are given relative to the directory containing the
    # wscript file. Providing absolute paths are best avoided as they are
    # a source of portability problems.
    includes = taskParams.get('includes', [])
    if includes:
        if isinstance(includes, stringtype):
            includes = includes.split()
        includes = [ x if os.path.isabs(x) else \
            joinpath(srcroot, x) for x in includes ]
    # The includes='.' add the build directory path. It's needed to use config
    # header with 'conftests'.
    includes.append('.')
    return includes

def fullclean(bconfPaths, verbose = 1):
    """
    It does almost the same thing as distclean from waf. But distclean can
    not remove directory with file wscript or symlink to it if distclean
    was called from that wscript.
    """

    import shutil

    def loginfo(msg):
        if verbose >= 1:
            log.info(msg)

    buildsymlink = bconfPaths.buildsymlink
    buildroot = bconfPaths.buildroot
    projectroot = bconfPaths.projectroot

    if buildsymlink:
        if os.path.isdir(buildsymlink) and not os.path.islink(buildsymlink):
            loginfo("Removing directory '%s'" % buildsymlink)
            shutil.rmtree(buildsymlink, ignore_errors = True)
        elif os.path.islink(buildsymlink) and os.path.lexists(buildsymlink):
            loginfo("Removing symlink '%s'" % buildsymlink)
            os.remove(buildsymlink)

    if os.path.exists(buildroot):
        realbuildroot = os.path.realpath(buildroot)
        if os.path.isdir(realbuildroot):
            loginfo("Removing directory '%s'" % realbuildroot)
            shutil.rmtree(realbuildroot, ignore_errors = True)

        if os.path.islink(buildroot) and os.path.lexists(buildroot):
            loginfo("Removing symlink '%s'" % buildroot)
            os.remove(buildroot)

    from waflib import Options
    lockfile = os.path.join(projectroot, Options.lockfile)
    if os.path.isfile(lockfile):
        loginfo("Removing lockfile '%s'" % lockfile)
        os.remove(lockfile)

    wscriptfile = os.path.join(projectroot, WSCRIPT_NAME)
    if os.path.isfile(wscriptfile):
        loginfo("Removing wscript file '%s'" % wscriptfile)
        os.remove(wscriptfile)

def distclean(bconfPaths):
    """
    Full replacement for distclean from WAF
    """

    cmdTimer = utils.Timer()

    verbose = 1
    import zm.cli as cli
    if cli.selected:
        colors = {'yes' : 2, 'auto' : 1, 'no' : 0}[cli.selected.args.color]
        log.enableColors(colors)
        verbose = cli.selected.args.verbose

    fullclean(bconfPaths, verbose)

    log.info('%r finished successfully (%s)', 'distclean', cmdTimer)

def isBuildConfFake(conf):
    """
    Return True if loaded buildconf is fake module.
    """
    return conf.__name__.endswith('fakebuildconf')

def _getBuildTypeFromCLI(clicmd):
    if not clicmd or not clicmd.args.buildtype:
        return ''
    return clicmd.args.buildtype

class BuildConfPaths(object):
    """
    Class to calculate different paths depending on buildconf
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, conf):
        dirname    = os.path.dirname
        abspath    = os.path.abspath
        unfoldPath = utils.unfoldPath

        self.buildconffile = abspath(conf.__file__)
        self.buildconfdir  = dirname(self.buildconffile)
        self.buildroot     = unfoldPath(self.buildconfdir, conf.buildroot)
        self.buildsymlink  = unfoldPath(self.buildconfdir, conf.buildsymlink)
        self.buildout      = joinpath(self.buildroot, BUILDOUTNAME)
        self.projectroot   = unfoldPath(self.buildconfdir, conf.project['root'])
        self.srcroot       = unfoldPath(self.buildconfdir, conf.srcroot)

        # TODO: add as option
        #self.wscripttop    = self.buildroot
        self.wscripttop    = self.projectroot

        self.wscriptout    = self.buildout
        self.wscriptfile   = joinpath(self.wscripttop, WSCRIPT_NAME)
        self.wscriptdir    = dirname(self.wscriptfile)
        self.wafcachedir   = joinpath(self.buildout, WAF_CACHE_DIRNAME)
        self.wafcachefile  = joinpath(self.wafcachedir, WAF_CACHE_NAMESUFFIX)
        self.zmcachedir    = self.wafcachedir
        self.zmcmnfile     = joinpath(self.buildout, ZENMAKE_COMMON_FILENAME)

    def __eq__(self, other):
        return vars(self) == vars(other)

class BuildConfHandler(object):
    """
    Class to handle data from buildconf
    """

    __slots__ = ('cmdLineHandled', '_conf', '_platforms', '_meta', '_confpaths')

    def __init__(self, conf):

        self.cmdLineHandled = False

        self._conf = conf
        self._platforms = self._conf.platforms

        self._meta = AutoDict()
        # just in case
        self._meta.buildtypes = AutoDict()

        self._confpaths = BuildConfPaths(conf)
        self._preprocess()

    def _preprocess(self):

        # NOTICE: this method should not have any heavy operations

        allBuildTypes = set(self._conf.buildtypes.keys())
        for taskParams in viewvalues(self._conf.tasks):
            taskBuildTypes = taskParams.get('buildtypes', {})
            allBuildTypes.update(taskBuildTypes.keys())
        self._meta.buildtypes.allnames = allBuildTypes

    def _handleTasksEnvVars(self, tasks):

        cinfo         = toolchains.CompilersInfo
        flagVars      = cinfo.allFlagVars()
        toolchainVars = cinfo.allVarsToSetCompiler()

        for taskParams in viewvalues(tasks):
            # handle flags
            for var in flagVars:
                envVal = os.environ.get(var, None)
                if not envVal:
                    continue

                paramName = var.lower()

                #current = taskParams.get(paramName, [])
                #current = utils.toList(current)
                # FIXME: should we add or replace?
                #taskParams[paramName] = current + utils.toList(envVal)
                taskParams[paramName] = utils.toList(envVal)

            # handle toolchains
            for var in toolchainVars:
                toolchain = os.environ.get(var, None)
                if not toolchain:
                    continue
                if var.lower() in taskParams.get('features', ''):
                    taskParams['toolchain'] = toolchain

    def _getRealBuildType(self, buildtype):

        if 'map' not in self._meta.buildtypes:
            btMap = dict()
            buildtypes = dict()
            buildtypes.update(self._conf.buildtypes)
            for btype in self._meta.buildtypes.allnames:
                if btype not in buildtypes:
                    buildtypes[btype] = {}
            for btype, val in viewitems(buildtypes):
                btVal = val
                btKey = btype
                while not isinstance(btVal, maptype):
                    if not isinstance(btVal, stringtype):
                        raise ZenMakeError("Invalid type of buildtype value '%s'"
                                           % type(btVal))
                    btKey = btVal
                    if btKey not in buildtypes:
                        raise ZenMakeError("Build type '%s' was not found, check "
                                           "your config." % btKey)
                    btVal = buildtypes[btKey]
                    if btKey == btype and btVal == val:
                        raise ZenMakeError("Circular reference was found")

                btMap[btype] = btKey

            self._meta.buildtypes.map = btMap

        btype = self._meta.buildtypes.map.get(buildtype, None)
        if not btype:
            raise ZenMakeError("Build type '%s' doesn't not exist"
                               " in buildconf." % buildtype)

        return btype

    def _checkCmdLineHandled(self):
        if not self.cmdLineHandled:
            raise ZenMakeLogicError("Command line args wasn't handled yet. "
                                    "You should call method handleCmdLineArgs.")

    def handleCmdLineArgs(self, clicmd):
        """
        Apply values from command line
        """

        if isBuildConfFake(self._conf):
            raise ZenMakeError('Config buildconf.py not found. Check buildconf.py '
                               'exists in the project directory.')

        buildtype = _getBuildTypeFromCLI(clicmd)

        supportedBuildTypes = self.supportedBuildTypes
        if buildtype not in supportedBuildTypes:
            raise ZenMakeError("Invalid choice for build type: '%s', "
                               "(choose from %s)" %
                               (buildtype, str(supportedBuildTypes)[1:-1]))

        self._meta.buildtypes.selected = self._getRealBuildType(buildtype)

        self.cmdLineHandled = True

    @property
    def conf(self):
        """ Get buildconf """
        return self._conf

    @property
    def projectName(self):
        """ Get project name """
        return self._conf.project['name']

    @property
    def projectVersion(self):
        """ Get project version """
        return self._conf.project['version']

    @property
    def confPaths(self):
        """ Get object of class BuildConfPaths """
        return self._confpaths

    @property
    def defaultBuildType(self):
        """ Get calculated default build type """

        if 'default' in self._meta.buildtypes:
            return self._meta.buildtypes.default

        buildtype = self._conf.buildtypes.get('default', '')
        if PLATFORM in self._platforms:
            buildtype = self._platforms[PLATFORM].get('default', buildtype)

        if buildtype and buildtype not in self._meta.buildtypes.allnames:
            raise ZenMakeError("Default build type '%s' was not found, "
                               "check your config." % buildtype)

        self._meta.buildtypes.default = buildtype
        return buildtype

    @property
    def selectedBuildType(self):
        """ Get selected build type """

        self._checkCmdLineHandled()
        return self._meta.buildtypes.selected

    @property
    def supportedBuildTypes(self):
        """
        Get calculated list of supported build types
        """

        if 'supported' in self._meta.buildtypes:
            return self._meta.buildtypes.supported

        supported = set()
        # handle 'buildconf.platforms'
        if PLATFORM in self._platforms:
            validBuildTypes = self._platforms[PLATFORM].get('valid', [])
            if not validBuildTypes:
                raise ZenMakeError("No valid build types for platform '%s' "
                                   "in config" % PLATFORM)
            for btype in validBuildTypes:
                if btype not in self._meta.buildtypes.allnames:
                    raise ZenMakeError("Build type '%s' for platform '%s' "
                                       "was not found, check your config." %
                                       (btype, PLATFORM))
            supported = set(validBuildTypes)
        else:
            supported.update(self._meta.buildtypes.allnames)

        if 'default' in supported:
            supported.remove('default')
        self._meta.buildtypes.supported = sorted(supported)

        return self._meta.buildtypes.supported

    @property
    def tasks(self):
        """
        Get all handled build tasks
        """

        self._checkCmdLineHandled()

        buildtype = self.selectedBuildType
        if buildtype in self._meta.tasks:
            return self._meta.tasks[buildtype]

        tasks = {}

        for taskName, taskParams in viewitems(self._conf.tasks):
            task = {}
            tasks[taskName] = task

            # 1. Copy exising params of selected buildtype from 'buildtypes'
            task.update(self._conf.buildtypes.get(buildtype, {}))

            # 2. Copy/replace existing params from origin task
            task.update(taskParams)
            if 'buildtypes' in task:
                del task['buildtypes']
            # 3. Copy/replace exising params of selected buildtype from 'tasks'
            taskBuildTypes = taskParams.get('buildtypes', {})
            taskBuildParams = taskBuildTypes.get(buildtype, {})
            task.update(taskBuildParams)

        self._handleTasksEnvVars(tasks)

        self._meta.tasks[buildtype] = tasks
        return tasks

    @property
    def toolchainNames(self):
        """
        Get unique names of all toolchains from current build tasks
        """

        if 'names' in self._meta.toolchains:
            return self._meta.toolchains.names

        self._checkCmdLineHandled()

        # gather unique names
        _toolchains = set()
        for taskParams in viewvalues(self.tasks):
            tool = taskParams.get('toolchain', None)
            if tool:
                _toolchains.add(tool)

        _toolchains = tuple(_toolchains)
        self._meta.toolchains.names = _toolchains
        return _toolchains

    @property
    def customToolchains(self):
        """
        Get 'custom' toolchains.
        """

        if 'custom' in self._meta.toolchains:
            return self._meta.toolchains.custom

        srcToolchains = self._conf.toolchains
        _customToolchains = AutoDict()
        for name, info in viewitems(srcToolchains):
            _vars = deepcopy(info) # don't change origin
            kind = _vars.pop('kind', None)
            if kind is None:
                raise ZenMakeError("Toolchain '%s': field 'kind' not found" % name)

            for k, v in viewitems(_vars):
                # try to identify path and do warning if not
                path = utils.unfoldPath(self._confpaths.projectroot, v)
                if not os.path.exists(path):
                    log.warn("Path to toolchain '%s' doesn't exists" % path)
                _vars[k] = path

            _customToolchains[name].kind = kind
            _customToolchains[name].vars = _vars

        self._meta.toolchains.custom = _customToolchains
        return _customToolchains
