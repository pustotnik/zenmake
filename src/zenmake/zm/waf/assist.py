# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some functions specific to use with the Waf.
"""

import os
import re
from copy import deepcopy

from waflib.ConfigSet import ConfigSet
from zm.pyutils import stringtype
from zm import utils, log, version, toolchains
from zm.error import ZenMakeError
from zm.constants import ZENMAKE_CACHE_NAMESUFFIX, CWD, TASK_FEATURE_ALIESES, PLATFORM
from zm.features import TASK_TARGET_FEATURES_TO_LANG, TASK_TARGET_FEATURES
from zm.features import SUPPORTED_TASK_FEATURES, resolveAliesesInFeatures
from zm.features import ToolchainVars, getLoadedFeatures

joinpath = os.path.join
normpath = os.path.normpath
relpath  = os.path.relpath
isabs    = os.path.isabs

_usedWafTaskKeys = set([
    'name', 'target', 'features', 'source', 'includes', 'lib', 'libpath',
    'rpath', 'use', 'vnum', 'idx', 'export_includes', 'export_defines',
    'install_path',
])

_srcCache = {}

def registerUsedWafTaskKeys(keys):
    ''' Register used Waf task keys '''
    _usedWafTaskKeys.update(keys)

def getUsedWafTaskKeys():
    ''' Get used Waf task keys '''
    return _usedWafTaskKeys

def getAllToolchainEnvVarNames():
    ''' Get all significant env vars for supported toolchains '''

    envVarNames = ToolchainVars.allFlagVars() + ToolchainVars.allVarsToSetToolchain()
    envVarNames += ('BUILDROOT',)

    return envVarNames

def dumpZenMakeCmnConfSet(monitfiles, filepath):
    """
    Dump ZenMake common ConfigSet file with some things like files
    monitored for changes.
    """

    zmCmn = ConfigSet()

    zmCmn.zmversion = version.current()

    zmCmn.monitfiles = sorted(set(monitfiles))
    zmCmn.monithash  = 0

    for file in zmCmn.monitfiles:
        zmCmn.monithash = utils.hashOfStrs((zmCmn.monithash,
                                            utils.readFile(file, 'rb')))

    zmCmn.toolenvs = {}
    envVarNames = getAllToolchainEnvVarNames()
    for name in envVarNames:
        zmCmn.toolenvs[name] = os.environ.get(name, '')

    zmCmn.store(filepath)

def loadZenMakeCmnConfSet(bconfPaths):
    """
    Load ZenMake common ConfigSet file. Return None if failed
    """

    zmCmn = ConfigSet()
    try:
        zmCmn.load(bconfPaths.zmcmnconfset)
    except EnvironmentError:
        return None

    return zmCmn

def makeCacheConfFileName(zmcachedir, name):
    """ Make file name of specific zenmake cache config file"""
    return joinpath(zmcachedir, name + ZENMAKE_CACHE_NAMESUFFIX)

def makeTaskVariantName(buildtype, taskName):
    """ Make 'variant' name for task """
    name = taskName.strip().replace(' ', '_')
    return '%s.%s' % (buildtype, re.sub(r'(?u)[^-\w.]', '.', name))

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

def delFromEnv(env, key):
    """
    Delete value from ConfigSet env.
    Operator 'del' doesn't work as expected with ConfigSet, see ConfigSet.__delitem__
    """

    try:
        while True:
            env.table.pop(key, None)
            env = env.parent
    except AttributeError:
        pass

def initBuildType(bconfManager, cliBuildType):
    """
    Init correct buildtype according CLI and buildconf.
    Returns resulting buildtype
    """

    bconf = bconfManager.root

    buildtype = cliBuildType
    if buildtype is None:
        buildtype = bconf.defaultBuildType
    if not buildtype and not isinstance(buildtype, stringtype):
        buildtype = ''

    for _bconf in bconfManager.configs:
        _bconf.applyBuildType(buildtype)

    return bconf.selectedBuildType

def applyInstallPaths(env, clicmd):
    """
    Apply installation path vars PREFIX, BINDIR, LIBDIR
    """

    opts = clicmd.args
    prefix = opts.get('prefix')
    bindir = opts.get('bindir')
    libdir = opts.get('libdir')

    if prefix and prefix != env.PREFIX:
        env.PREFIX = prefix
        if not bindir:
            env.BINDIR = '%s/bin' % prefix
        if not libdir:
            env.LIBDIR = '%s/lib%s' % (prefix, utils.libDirPostfix())

    if bindir:
        env.BINDIR = bindir
    if libdir:
        env.LIBDIR = libdir

    for var in ('PREFIX', 'BINDIR', 'LIBDIR'):
        if var not in env:
            continue
        val = env[var]
        if not isabs(val):
            env[var] = '/' + val

def setTaskToolchainEnvVars(env, taskParams):
    """
    Set up some env vars for build task such as compiler flags
    """

    cfgEnvVars = ToolchainVars.allCfgEnvVars()
    for var in cfgEnvVars:
        val = taskParams.get(var.lower(), None)
        if val:
            # Waf has some usefull predefined env vars for some compilers
            # so here we add values, not replace them.
            env[var] += utils.toList(val)

def getValidPreDefinedToolchainNames():
    """
    Return set of valid names of predefined toolchains (without custom toolchains)
    """

    langs = set(getLoadedFeatures()).intersection(ToolchainVars.allLangs())
    validNames = {'auto-' + lang.replace('x', '+') for lang in langs}
    validNames.update(toolchains.getAll(platform = PLATFORM))
    return validNames

def getTaskNamesWithDeps(tasks, names):
    """
    Gather all task names including tasks in 'use'
    """
    result = list(names)
    for name in names:
        params = tasks.get(name, {})
        deps = params.get('use')
        if deps:
            result.extend(getTaskNamesWithDeps(tasks, utils.toList(deps)))

    return result

def aliesInFeatures(features):
    """ Return True if any alies exists in features """

    return bool(TASK_FEATURE_ALIESES.intersection(features))

def detectTaskFeatures(ctx, taskParams):
    """
    Detect all features for task
    Param 'ctx' is used only if an alies exists in features.
    """

    features = utils.toList(taskParams.get('features', []))
    if aliesInFeatures(features):
        features = handleTaskFeatureAlieses(ctx, features, taskParams.get('source'))

    detected = [ TASK_TARGET_FEATURES_TO_LANG.get(x, '') for x in features ]
    features = detected + features

    features = utils.uniqueListWithOrder(features)
    if '' in features:
        features.remove('')
    taskParams['features'] = features

    return features

_RE_EXT_AT_THE_END = re.compile(r'\.\w+$')

def handleTaskFeatureAlieses(ctx, features, source):
    """
    Detect features for alieses 'stlib', 'shlib', 'program' and 'objects'
    """

    if source is None:
        return features

    assert source

    if source.get('paths') is None:
        patterns = utils.toList(source.get('include', ''))
        #ignorecase = source.get('ignorecase', False)
        #if ignorecase:
        #    patterns = [x.lower() for x in patterns]

        for pattern in patterns:
            if not _RE_EXT_AT_THE_END.search(pattern):
                msg = "Pattern %r in 'source'" % pattern
                msg += " must have some file extension at the end."
                raise ZenMakeError(msg)

    source = handleTaskSourceParam(ctx, source)
    return resolveAliesesInFeatures(source, features)

def validateConfTaskFeatures(taskParams):
    """
    Check all features are valid and remove unsupported features
    """

    features = taskParams['features']
    unknown = [x for x in features if x not in SUPPORTED_TASK_FEATURES]
    if unknown:
        for val in unknown:
            features.remove(val)
            msg = 'Feature %r in task %r is not supported. Removed.' % \
                  (val, taskParams['name'])
            log.warn(msg)
    taskParams['features'] = features
    return features

def _makeTaskPathParam(param, rootdir, startdir, relative = True):
    """
    Make correct param with path(s) according to param and task stardir
    """

    # rootdir and startdir parameters must have absolute paths

    # param['startdir'] is relative to rootdir and can be different from
    # the task startdir

    # Must have this key, otherwise it's a programming error
    _startdir = param['startdir']
    # make valid absolute path for current param
    _startdir = joinpath(rootdir, _startdir)

    paths = utils.toList(param['paths'])
    result = []
    for path in paths:
        path = utils.getNativePath(path)
        if not isabs(path):
            path = joinpath(_startdir, path)
        if relative:
            # make path relative to the task startdir
            path = normpath(relpath(path, startdir))
        result.append(path)

    return result

def handleTaskLibPathParam(taskParams, rootdir, startdir):
    """
    Make valid 'libpath' for build task
    """

    paramName = 'libpath'
    param = taskParams.get(paramName, None)
    if param is None:
        return

    # Waf doesn't change 'libpath' relative to current ctx.path as for 'includes'.
    # So we use absolute paths here.
    taskParams[paramName] = _makeTaskPathParam(
                param, rootdir, startdir, relative = False)

def handleTaskIncludesParam(taskParams, rootdir, startdir):
    """
    Make valid 'includes' and 'export-includes' for build task
    """

    # From wafbook:
    # Includes paths are given relative to the directory containing the
    # wscript file. Providing absolute paths are best avoided as they are
    # a source of portability problems.

    #####################
    ### 'includes'

    if 'includes' in taskParams:
        param = taskParams['includes']
        includes = _makeTaskPathParam(param, rootdir, startdir)
    else:
        includes = []

    # The includes='.' add the startdir.
    # To save the same order with the Waf 'export_includes'
    # it's inserted in front of the list.
    includes.insert(0, '.')
    taskParams['includes'] = includes

    #####################
    ### 'export-includes'

    if 'export-includes' not in taskParams:
        return

    param = taskParams['export-includes']
    # Must have this key, otherwise it's a programming error
    exportIncludes = param['paths']
    if not exportIncludes:
        taskParams.pop('export-includes', None)
        return

    if isinstance(exportIncludes, bool) and exportIncludes:
        exportIncludes = includes
    else:
        exportIncludes = _makeTaskPathParam(param, rootdir, startdir)
    taskParams['export-includes'] = exportIncludes

def handleTaskExportDefinesParam(taskParams):
    """
    Get valid 'export-defines' for build task
    """

    exportDefines = taskParams.get('export-defines', None)
    if not exportDefines:
        taskParams.pop('export-defines', None)
        return

    if isinstance(exportDefines, bool) and exportDefines:
        exportDefines = taskParams.get('defines', [])

    taskParams['export-defines'] = utils.toList(exportDefines)

def handleTaskSourceParam(ctx, src):
    """
    Get valid 'source' for build task
    """

    if not src:
        return []

    cacheKey = hash( repr(sorted(src.items())) )
    cached = _srcCache.get(cacheKey)
    if cached is not None:
        return [ctx.root.make_node(x) for x in cached]

    bconf = ctx.getbconf()
    startdir = joinpath(bconf.rootdir, src['startdir'])

    # Path must be relative to the ctx.path
    srcDir = relpath(startdir, ctx.path.abspath())

    # Since ant_glob can traverse both source and build folders, it is a best
    # practice to call this method only from the most specific build node.
    srcDirNode = ctx.path.find_dir(srcDir)

    files = src.get('paths', None)
    if files is not None:
        # process each source file
        files = utils.toList(files)
        result = []
        for file in files:
            assert isinstance(file, stringtype)
            v = srcDirNode.find_node(file)
            if v:
                result.append(v)
            else:
                msg = "Error in the buildconf file %r:" % relpath(bconf.path, CWD)
                msg += "\nFile %r from the 'source' not found." % file
                raise ZenMakeError(msg)
    else:
        result = srcDirNode.ant_glob(
            incl = src.get('include', ''),
            excl = src.get('exclude', ''),
            ignorecase = src.get('ignorecase', False),
            #FIXME: Waf says: Calling ant_glob on build folders is
            # dangerous. Such a case can be seen if build
            # the demos/cpp/002-simple
            remove = False,
        )

    _srcCache[cacheKey] = [x.abspath() for x in result]
    return result

def checkWafTasksForFeatures(taskParams):
    """
    Validate current features with loaded Waf task classes
    """

    from waflib import Task

    # check only supported Waf features
    features = tuple(TASK_TARGET_FEATURES & set(taskParams['features']))
    for feature in features:
        if feature not in Task.classes:
            msg = "Feature %r can not be processed for task %r." % \
                  (feature, taskParams['name'])
            msg += " Maybe you didn't set correct toolchain for this task."
            raise ZenMakeError(msg)

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
    startdir      = bconfPaths.startdir

    assert not startdir.startswith(buildroot)
    assert not startdir.startswith(realbuildroot)

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
    lockfile = os.path.join(startdir, Options.lockfile)
    if os.path.isfile(lockfile):
        loginfo("Removing lockfile '%s'" % lockfile)
        os.remove(lockfile)

def distclean(bconfPaths):
    """
    Implementation for distclean from WAF
    """

    verbose = 1
    from zm import cli
    cmd = cli.selected
    if cmd:
        verbose = cmd.args.verbose

    fullclean(bconfPaths, verbose)

def printZenMakeHeader(bconfManager):
    """
    Log header with some info.
    """

    bconf = bconfManager.root
    log.info("* Project name: '%s'" % bconf.projectName)
    log.info("* Project version: %s" % (bconf.projectVersion or 'undefined'))
    log.info("* Build type: '%s'" % bconf.selectedBuildType)

def isBuildConfFake(conf):
    """
    Return True if loaded buildconf is a fake module.
    """
    return conf.__name__.endswith('fakeconf')

def areMonitoredFilesChanged(zmCmnConfSet):
    """
    Detect that current monitored files are changed.
    """

    _hash = 0
    for file in zmCmnConfSet.monitfiles:
        try:
            _hash = utils.hashOfStrs((_hash, utils.readFile(file, 'rb')))
        except EnvironmentError:
            return True

    return _hash != zmCmnConfSet.monithash

def areToolchainEnvVarsAreChanged(zmCmnConfSet):
    """
    Detect that current toolchain env vars are changed.
    """

    lastEnvVars = zmCmnConfSet.toolenvs
    envVarNames = getAllToolchainEnvVarNames()
    for name in envVarNames:
        if name not in lastEnvVars:
            return True
        if lastEnvVars[name] != os.environ.get(name, ''):
            return True

    return False

def isZmVersionChanged(zmCmnConfSet):
    """
    Detect that current version of ZenMake was changed from last building .
    """

    return zmCmnConfSet.zmversion != version.current()

def isBuildConfChanged(buildconf, buildroot):
    """
    Try to detect if current buildconf file is changed.
    Returns True if it's changed or file just doesn't exist.
    """

    # FIXME: remake
    raise NotImplementedError

    #from zm.buildconf.paths import ConfPaths
    #try:
    #    bconfPaths = ConfPaths(buildconf, buildroot)
    #except AttributeError:
    #    return True
    #
    #cmnConfSet = loadZenMakeCmnConfSet(bconfPaths)
    #if not cmnConfSet:
    #    return True
    #
    #return areMonitoredFilesChanged(cmnConfSet)
