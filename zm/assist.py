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
from zm.pyutils import stringtype, viewitems
from zm import utils, toolchains, log
from zm.constants import ZENMAKE_CACHE_NAMESUFFIX, WSCRIPT_NAME

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
    taskName = taskParams['name']
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
            def defaultFileName():
                return utils.normalizeForFileName(taskName).lower()
            fileName = entity.pop('file', '%s_%s' %
                                  (defaultFileName(), 'config.h'))
            fileName = joinpath(buildtype, fileName)
            projectName = cfgCtx.env['PROJECT_NAME'] or ''
            guardname = utils.normalizeForDefine(projectName + '_' + fileName)
            entity['guard'] = entity.pop('guard', guardname)
            cfgCtx.write_config_header(fileName, **entity)
        else:
            cfgCtx.fatal('unknown act %r for conftests in task %r!' %
                         (act, taskName))

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
        cfgCtx.fatal("No toolchains found. Is buildconf correct?")

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

def detectAllTaskFeatures(taskParams):
    """
    Detect all features for task
    """
    features = utils.toList(taskParams.get('features', []))
    fmap = {
        'cprogram' : 'c',
        'cxxprogram' : 'cxx',
        'cstlib' : 'c',
        'cxxstlib' : 'cxx',
        'cshlib' : 'c',
        'cxxshlib' : 'cxx',
    }
    detected = [ fmap.get(x, '') for x in features ]

    if taskParams.get('use-as-test', False):
        detected.append('test')

    features.extend(detected)
    features = set(features)
    if '' in features:
        features.remove('')
    return list(features)

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
    Return True if loaded buildconf is a fake module.
    """
    return conf.__name__.endswith('fakeconf')

def areMonitoredFilesChanged(bconfPaths):
    """
    Try to detect if current monitored files are changed.
    """

    zmCmn = ConfigSet()
    try:
        zmcmnfile = bconfPaths.zmcmnfile
        zmCmn.load(zmcmnfile)
    except EnvironmentError:
        return True

    _hash = 0
    for file in zmCmn.monitfiles:
        try:
            _hash = utils.mkHashOfStrings((_hash, utils.readFile(file, 'rb')))
        except EnvironmentError:
            return True

    return _hash != zmCmn.monithash

def isBuildConfChanged(conf):
    """
    Try to detect if current buildconf file is changed.
    Returns True if it's changed or file just doesn't exist.
    """

    from zm.buildconf.paths import BuildConfPaths
    try:
        bconfPaths = BuildConfPaths(conf)
    except AttributeError:
        return True

    return areMonitoredFilesChanged(bconfPaths)
