# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 There are functions and classes specific to process with our wscript.
"""

import os
import re
from copy import deepcopy
from collections import defaultdict

from waflib.ConfigSet import ConfigSet
from waflib import Errors as waferror
from zm.pyutils import stringtype, maptype, viewitems
from zm import utils, toolchains, log
from zm.constants import ZENMAKE_CACHE_NAMESUFFIX, WSCRIPT_NAME

joinpath = os.path.join

_usedWafTaskKeys = set([
    'name', 'target', 'features', 'source', 'includes', 'lib', 'libpath',
    'rpath', 'use', 'vnum', 'idx'
])

def registerUsedWafTaskKeys(keys):
    ''' Register used Waf task keys '''
    _usedWafTaskKeys.update(keys)

def getUsedWafTaskKeys():
    ''' Get used Waf task keys '''
    return _usedWafTaskKeys

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

def makeCacheConfFileName(zmcachedir, name):
    """ Make file name of specific zenmake cache config file"""
    return joinpath(zmcachedir, name + ZENMAKE_CACHE_NAMESUFFIX)

def makeTaskVariantName(buildtype, taskName):
    """ Make 'variant' name for task """
    name = taskName.strip().replace(' ', '_')
    return '%s.%s' % (buildtype, re.sub(r'(?u)[^-\w.]', '.', name))

WSCRIPT_BODY = '''\
# coding=utf-8

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module is entry WAF wscript file that is copied from zenmake.

 Do not commit this to version control.
"""

from zm.wscriptimpl import *
'''

def writeWScriptFile(filepath):
    """ Write 'wscript' file """

    with open(filepath, 'w') as file:
        file.write(WSCRIPT_BODY)

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

def setConfDirectEnv(cfgCtx, name, env):
    """ Set env without deriving and other actions """

    cfgCtx.variant = name
    cfgCtx.all_envs[name] = env

def setTaskEnvVars(env, taskParams):
    """
    Set up some env vars for build task such as compiler flags
    """

    cfgEnvVars = toolchains.CompilersInfo.allCfgEnvVars()
    for var in cfgEnvVars:
        val = taskParams.get(var.lower(), None)
        if val:
            # Waf has some usefull predefined env vars for some compilers
            # so here we add values, not replace them.
            env[var] += utils.toList(val)

def _confTestCheckPrograms(entity, **kwargs):
    cfgCtx = kwargs['cfgCtx']

    cfgCtx.setenv('')
    called = kwargs['called'][id(cfgCtx.env)]

    names = utils.toList(entity.pop('names', []))
    funcArgs = entity
    funcArgs['path_list'] = utils.toList(entity.pop('paths', []))

    for name in names:
        # It doesn't matter here that 'hash' can produce different result
        # between python runnings.
        _hash = hash( ('find_program', name, repr(sorted(funcArgs.items())) ) )
        if _hash not in called:
            cfgCtx.find_program(name, **funcArgs)
            called.add(_hash)

def _confTestCheck(entity, **kwargs):
    cfgCtx = kwargs['cfgCtx']
    taskParams = kwargs['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])
    called = kwargs['called'][id(cfgCtx.env)]
    funcArgs = entity
    _hash = hash( ('check', repr(sorted(funcArgs.items())) ) )
    if _hash not in called:
        cfgCtx.check(**funcArgs)
        called.add(_hash)

def _confTestCheckSysLibs(entity, **kwargs):
    taskParams = kwargs['taskParams']

    sysLibs = utils.toList(taskParams.get('sys-libs', []))
    funcArgs = entity
    for lib in sysLibs:
        funcArgs['lib'] = lib
        _confTestCheck(funcArgs, **kwargs)

def _confTestCheckHeaders(entity, **kwargs):
    headers = utils.toList(entity.pop('names', []))
    funcArgs = entity
    for header in headers:
        funcArgs['header_name'] = header
        _confTestCheck(funcArgs, **kwargs)

def _confTestCheckLibs(entity, **kwargs):
    libs = utils.toList(entity.pop('names', []))
    autodefine = entity.pop('autodefine', False)
    funcArgs = entity
    for lib in libs:
        funcArgs['lib'] = lib
        if autodefine:
            funcArgs['define_name'] = 'HAVE_LIB_' + lib.upper()
        _confTestCheck(funcArgs, **kwargs)

def _confTestWriteHeader(entity, **kwargs):

    buildtype  = kwargs['buildtype']
    cfgCtx     = kwargs['cfgCtx']
    taskName   = kwargs['taskName']
    taskParams = kwargs['taskParams']

    cfgCtx.setenv(taskParams['$task.variant'])

    def defaultFileName():
        return utils.normalizeForFileName(taskName).lower()

    fileName = entity.pop('file', '%s_%s' %
                          (defaultFileName(), 'config.h'))
    fileName = joinpath(buildtype, fileName)
    projectName = cfgCtx.env['PROJECT_NAME'] or ''
    guardname = utils.normalizeForDefine(projectName + '_' + fileName)
    entity['guard'] = entity.pop('guard', guardname)

    cfgCtx.write_config_header(fileName, **entity)

_confTestFuncs = {
    'check-programs'      : _confTestCheckPrograms,
    'check-sys-libs'      : _confTestCheckSysLibs,
    'check-headers'       : _confTestCheckHeaders,
    'check-libs'          : _confTestCheckLibs,
    'check'               : _confTestCheck,
    'write-config-header' : _confTestWriteHeader,
}

def runConfTests(cfgCtx, buildtype, tasks):
    """
    Run supported configuration tests/checks
    """

    called = defaultdict(set)

    for taskName, taskParams in viewitems(tasks):
        confTests = taskParams.get('conftests', [])
        funcKWArgs = dict(
            cfgCtx = cfgCtx,
            buildtype = buildtype,
            taskName = taskName,
            taskParams = taskParams,
            called = called,
        )
        for entity in confTests:
            entity = entity.copy()
            act = entity.pop('act', None)
            func = _confTestFuncs.get(act, None)
            if not func:
                cfgCtx.fatal('unknown act %r for conftests in task %r!' %
                             (act, taskName))

            func(entity, **funcKWArgs)

    cfgCtx.setenv('')

def _loadDetectedCompiler(cfgCtx, lang):
    """
    Load auto detected compiler by its lang
    """

    compilers = toolchains.CompilersInfo.compilers(lang)
    envVar    = toolchains.CompilersInfo.varToSetCompiler(lang)

    for compiler in compilers:
        cfgCtx.env.stash()
        cfgCtx.start_msg('Checking for %r' % compiler)
        try:
            cfgCtx.load(compiler)
        except waferror.ConfigurationError:
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

    toolchainsEnvs = {}
    oldEnvName = cfgCtx.variant

    def loadToolchain(toolchain):
        toolname = toolchain
        if toolname in toolchainsEnvs:
            #don't load again
            return

        cfgCtx.setenv(toolname, env = copyFromEnv)
        custom  = buildconfHandler.customToolchains.get(toolname, None)
        if custom is not None:
            for var, val in viewitems(custom.vars):
                cfgCtx.env[var] = val
            toolchain = custom.kind

        if toolchain.startswith('auto-'):
            lang = toolchain[5:]
            _loadDetectedCompiler(cfgCtx, lang)
        else:
            cfgCtx.load(toolchain)
        toolchainsEnvs[toolname] = cfgCtx.env

    for toolchain in buildconfHandler.toolchainNames:
        loadToolchain(toolchain)

    # switch to old env due to calls of 'loadToolchain'
    cfgCtx.setenv(oldEnvName)

    return toolchainsEnvs

def detectAllTaskFeatures(taskParams):
    """
    Detect all features for task
    """
    features = utils.toList(taskParams.get('features', []))
    if not features and 'run' in taskParams:
        return ['runcmd']

    fmap = {
        'cprogram' : 'c',
        'cxxprogram' : 'cxx',
        'cstlib' : 'c',
        'cxxstlib' : 'cxx',
        'cshlib' : 'c',
        'cxxshlib' : 'cxx',
    }
    detected = [ fmap.get(x, '') for x in features ]

    features.extend(detected)
    features = set(features)
    if '' in features:
        features.remove('')
    return list(features)

def handleTaskIncludesParam(taskParams, srcroot):
    """
    Get valid 'includes' for build task
    """

    if 'includes' not in taskParams:
        features = taskParams['features']
        needIncludes = any([x for x in features if x in ('c', 'cxx')])
        if not needIncludes:
            return None

    # From wafbook:
    # Includes paths are given relative to the directory containing the
    # wscript file. Providing absolute paths are best avoided as they are
    # a source of portability problems.
    includes = taskParams.get('includes', [])
    if includes:
        includes = utils.toList(includes)
        includes = [ x if os.path.isabs(x) else \
            joinpath(srcroot, x) for x in includes ]
    # The includes='.' add the build directory path. It's needed to use config
    # header with 'conftests'.
    includes.append('.')
    return includes

def handleTaskSourceParam(taskParams, srcDirNode):
    """
    Get valid 'source' for build task
    """

    src = taskParams.get('source')
    if not src:
        return []

    if isinstance(src, maptype):
        return srcDirNode.ant_glob(
            incl = src.get('include', ''),
            excl = src.get('exclude', ''),
            ignorecase = src.get('ignorecase', False),
            #FIXME: Waf says: Calling ant_glob on build folders is
            # dangerous. Such a case can be seen if build
            # the tests/projects/cpp/002-simple
            remove = False,
        )

    # process each source file
    src = utils.toList(src)
    result = []
    for v in src:
        if isinstance(v, stringtype):
            v = srcDirNode.find_node(v)
        if v:
            result.append(v)
    return result

def configureTaskParams(cfgCtx, confHandler, taskName, taskParams):
    """
    Handle every known task param that can be handled at configure stage.
    It is better for common performance because command 'configure' is used
    rarely then 'build'.
    """

    bconfPaths = confHandler.confPaths
    btypeDir = confHandler.selectedBuildTypeDir

    taskParams['features'] = features = detectAllTaskFeatures(taskParams)

    normalizeTarget = taskParams.get('normalize-target-name', False)
    target = taskParams.get('target', taskName)
    if normalizeTarget:
        target = utils.normalizeForFileName(target, spaseAsDash = True)
    targetPath = joinpath(btypeDir, target)

    kwargs = dict(
        name     = taskName,
        target   = targetPath,
        #counter for the object file extension
        idx      = taskParams.get('object-file-counter', 1),
    )

    nameMap = (
        ('sys-libs','lib'),
        ('sys-lib-path','libpath'),
        ('rpath','rpath'),
        ('use', 'use'),
    )
    for param in nameMap:
        value = taskParams.get(param[0], None)
        if value is not None:
            kwargs[param[1]] = utils.toList(value)

    vnum = taskParams.get('ver-num', None)
    if vnum:
        kwargs['vnum'] = vnum

    includes = handleTaskIncludesParam(taskParams, bconfPaths.srcroot)
    if includes:
        kwargs['includes'] =  includes

    # set of used keys in kwargs must be included in set from getUsedWafTaskKeys()
    assert set(kwargs.keys()) <= getUsedWafTaskKeys()

    taskParams.update(kwargs)

    taskVariant = taskParams['$task.variant']
    taskEnv = cfgCtx.all_envs[taskVariant]

    runnable = False
    realTarget = targetPath
    for feature in features:
        pattern = taskEnv[feature + '_PATTERN']
        if pattern:
            realTarget = joinpath(btypeDir, pattern % target)
        if feature.endswith('program'):
            runnable = True

    taskParams['$real.target'] = realTarget
    taskParams['$runnable'] = runnable

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

    realbuildroot = bconfPaths.realbuildroot
    buildroot     = bconfPaths.buildroot
    projectroot   = bconfPaths.projectroot

    paths = [realbuildroot, buildroot]
    for path in list(paths):
        paths.append(os.path.realpath(path))
    paths = list(set(paths))

    for path in paths:
        if os.path.isdir(path) and not os.path.islink(path):
            loginfo("Removing directory '%s'" % path)
            shutil.rmtree(path, ignore_errors = True)

        if os.path.islink(path):
            loginfo("Removing symlink '%s'" % path)
            os.remove(path)

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
        log.enableColorsByCli(cli.selected.args.color)
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
