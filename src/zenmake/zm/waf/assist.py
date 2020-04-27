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
from zm.pyutils import viewitems, stringtype, _unicode, _encode
from zm.autodict import AutoDict as _AutoDict
from zm.pathutils import getNodesFromPathsDict
from zm import utils, log, version, toolchains, db
from zm.error import ZenMakeError, ZenMakeConfError
from zm.error import ZenMakePathNotFoundError, ZenMakeDirNotFoundError
from zm.constants import TASK_FEATURE_ALIESES, PLATFORM
from zm.features import TASK_TARGET_FEATURES_TO_LANG, TASK_TARGET_FEATURES
from zm.features import SUPPORTED_TASK_FEATURES, resolveAliesesInFeatures
from zm.features import ToolchainVars, getLoadedFeatures

joinpath = os.path.join
normpath = os.path.normpath
relpath  = os.path.relpath
isabs    = os.path.isabs

toList       = utils.toList
toListSimple = utils.toListSimple

# These keys are not removed from waf task gen on 'build' step
# Such keys as '*flags' and 'defines' are set in task envs, so they
# don't need to be protected from removing from waf task gen.
_usedWafTaskKeys = set([
    'name', 'target', 'features', 'source', 'includes',
    'lib', 'libpath', 'monitlibs', 'stlib', 'stlibpath', 'monitstlibs',
    'rpath', 'use', 'vnum', 'idx', 'export_includes', 'export_defines',
    'install_path',
])

_srcCache = {}

_RE_TASKVARIANT_NAME = re.compile(r'[^-\w.]', re.UNICODE)
_RE_EXT_AT_THE_END = re.compile(r'\.\w+$', re.UNICODE)

def registerUsedWafTaskKeys(keys):
    ''' Register used Waf task keys '''
    _usedWafTaskKeys.update(keys)

def getUsedWafTaskKeys():
    ''' Get used Waf task keys '''
    return _usedWafTaskKeys

def getAllToolchainEnvVarNames():
    ''' Get all significant env vars for supported toolchains '''

    envVarNames = ToolchainVars.allSysFlagVars()
    envVarNames += ToolchainVars.allSysVarsToSetToolchain()
    envVarNames += ('BUILDROOT',)

    return envVarNames

def writeZenMakeMetaFile(bconfPaths, monitfiles, attrs):
    """
    Write ZenMake meta file with some things like files
    monitored for changes.
    """

    zmMeta = _AutoDict()
    zmMeta.zmversion = version.current()
    zmMeta.platform = PLATFORM

    zmMeta.attrs = attrs
    zmMeta.monitfiles = sorted(set(monitfiles))
    zmMeta.monithash  = utils.hashFiles(zmMeta.monitfiles)

    zmMeta.toolenvs = {}
    envVarNames = getAllToolchainEnvVarNames()
    for name in envVarNames:
        zmMeta.toolenvs[name] = os.environ.get(name, '')

    from waflib import Context
    zmMeta.rundir = Context.run_dir
    zmMeta.topdir = Context.top_dir
    zmMeta.outdir = Context.out_dir

    dbfile = db.PyDBFile(bconfPaths.zmmetafile, extension = '')
    dbfile.save(zmMeta)

def loadZenMakeMetaFile(bconfPaths):
    """
    Load ZenMake common ConfigSet file. Return None if failed
    """

    dbfile = db.PyDBFile(bconfPaths.zmmetafile, extension = '')
    try:
        data = dbfile.load(asConfigSet = True)
    except EnvironmentError:
        return None

    return data

def makeTasksCachePath(zmcachedir, buildtype):
    """ Make file path of zenmake tasks cache file for selected buildtype"""
    name = "%s.tasks" % buildtype
    return joinpath(zmcachedir, name)

def makeTaskVariantName(buildtype, taskName):
    """ Make 'variant' name for task """

    name = _unicode(taskName).strip().replace(' ', '_')
    name = '%s.%s' % (buildtype, _RE_TASKVARIANT_NAME.sub('.', name))
    return _encode(name)

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

def setTaskEnvVars(env, taskParams, toolchainSettings):
    """
    Set up some env vars for build task such as compiler flags
    """

    # Right order:
    # waf env + bconf + sys env

    _gathered = {}

    # all Waf env vars that can be set from buildconf params
    cfgFlagVars = ToolchainVars.allCfgFlagVars()
    # read flags from the buildconf and USELIB_VARS
    for var in cfgFlagVars:
        paramName = var.lower()
        val = taskParams.get(paramName)
        if val:
            # bconf
            _gathered[var] = toList(val)

    # apply vars from toolchain settings that include env vars
    sysFlagVars = ToolchainVars.allSysFlagVars()
    for toolchain in taskParams['toolchain']:
        assert toolchain in toolchainSettings
        settingVars = toolchainSettings[toolchain].vars
        for var in sysFlagVars:
            val = settingVars.get(var)
            if val:
                # bconf + (toolchains + sys env)
                _gathered[var] = _gathered.get(var, []) + val

    # merge with the waf env vars
    for var, val in viewitems(_gathered):
        # Waf has some usefull predefined env vars for some compilers
        # so here we add values, not replace them.

        # waf env + (bconf + toolchains + sys env)
        val = env[var] + val

        # remove duplicates: keep only last unique values in the list
        val = utils.uniqueListWithOrder(reversed(val))
        val.reverse()
        env[var] = val

def getValidPreDefinedToolchainNames():
    """
    Return set of valid names of predefined toolchains (without custom toolchains)
    """

    langs = set(getLoadedFeatures()).intersection(ToolchainVars.allLangs())
    validNames = {'auto-' + lang.replace('xx', '++') for lang in langs}
    validNames.update(toolchains.getAllNames(platform = PLATFORM))
    return validNames

def getTaskNamesWithDeps(tasks, names):
    """
    Gather all task names including tasks in 'use'
    """
    result = list(names)
    for name in names:
        deps = tasks.get(name, {}).get('use')
        if deps is not None:
            result.extend(getTaskNamesWithDeps(tasks, toList(deps)))

    return result

def convertTaskParamNamesForWaf(taskParams):
    """
    Replace some ZenMake names with Waf names
    """

    nameMap = (
        ('libs', 'lib'),
        ('stlibs', 'stlib'),
        ('ver-num', 'vnum'),
        ('export-includes', 'export_includes'),
        ('export-defines', 'export_defines'),
        ('install-path', 'install_path'),
        ('objfile-index', 'idx'),
    )

    for zmKey, wafKey in nameMap:
        val = taskParams.pop(zmKey, None)
        if val is not None:
            taskParams[wafKey] = val

def aliesInFeatures(features):
    """ Return True if any alies exists in features """

    return bool(TASK_FEATURE_ALIESES.intersection(features))

def detectTaskFeatures(ctx, taskParams):
    """
    Detect all features for task
    Param 'ctx' is used only if an alies exists in features.
    """

    features = toListSimple(taskParams.get('features', []))
    if aliesInFeatures(features):
        features = handleTaskFeatureAlieses(ctx, features, taskParams.get('source'))

    detected = [ TASK_TARGET_FEATURES_TO_LANG.get(x, '') for x in features ]
    features = detected + features

    if 'run' in taskParams:
        features.append('runcmd')

    features = utils.uniqueListWithOrder(features)
    if '' in features:
        features.remove('')
    taskParams['features'] = features

    return features

def handleTaskFeatureAlieses(ctx, features, source):
    """
    Detect features for alieses 'stlib', 'shlib', 'program' and 'objects'
    """

    if source is None:
        return features

    assert source

    if source.get('paths') is None:
        patterns = toList(source.get('include', []))
        #ignorecase = source.get('ignorecase', False)
        #if ignorecase:
        #    patterns = [x.lower() for x in patterns]

        for pattern in patterns:
            if not _RE_EXT_AT_THE_END.search(_unicode(pattern)):
                msg = "Pattern %r in 'source'" % pattern
                msg += " must have some file extension at the end."
                raise ZenMakeConfError(msg)

    source = handleTaskSourceParam(ctx, source)
    return resolveAliesesInFeatures(source, features)

def validateTaskFeatures(taskParams):
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

    if not features and taskParams.get('source'):
        msg = "There is no way to proccess task %r" % taskParams['name']
        msg += " with empty 'features'."
        msg += " You need to specify 'features' for this task."
        raise ZenMakeConfError(msg)

    return features

def handleTaskLibPathParams(taskParams):
    """
    Make valid 'libpath','stlibpath' for a build task
    """

    for paramName in ('libpath', 'stlibpath'):
        param = taskParams.get(paramName)
        if param is None:
            continue

        # Waf doesn't change 'libpath' relative to current ctx.path as for 'includes'.
        # So we use absolute paths here.
        taskParams[paramName] = param.abspaths()

def handleTaskIncludesParam(taskParams, startdir):
    """
    Make valid 'includes' and 'export-includes' for build task
    """

    # Includes paths must be relative to the startdir

    #####################
    ### 'includes'

    if 'includes' in taskParams:
        param = taskParams['includes']
        param.startdir = startdir
        includes = param.relpaths()
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
    if isinstance(param, bool):
        exportIncludes = includes if param else None
    else:
        param.startdir = startdir
        exportIncludes = param.relpaths()

    if not exportIncludes:
        taskParams.pop('export-includes', None)
        return

    taskParams['export-includes'] = exportIncludes

def handleTaskSourceParam(ctx, src):
    """
    Get valid 'source' for build task
    """

    if not src:
        return []

    pathsWithPattern = not src.get('paths')
    if pathsWithPattern:
        # There is no reasons to cache lists of paths and
        # the cache key for them can be too big
        cacheKey = repr(sorted(src.items()))
        cached = _srcCache.get(cacheKey)
        if cached is not None:
            return [ctx.root.make_node(x) for x in cached]

    bconf = ctx.getbconf()

    try:
        buildrootNode = ctx.brootNode
    except AttributeError:
        buildroot = bconf.confPaths.buildroot
        buildrootNode = ctx.root.make_node(buildroot)
        ctx.brootNode = buildrootNode

    try:
        result = getNodesFromPathsDict(ctx, src, bconf.rootdir,
                                       excludeExtraPaths = [buildrootNode])
    except ZenMakeDirNotFoundError as ex:
        msg = "Directory %r for the 'source' doesn't exist." % ex.path
        raise ZenMakeError(msg)
    except ZenMakePathNotFoundError as ex:
        msg = "Error in the file %r:" % bconf.path
        msg += "\n  File %r from the 'source' not found." % ex.path
        raise ZenMakeError(msg)

    if pathsWithPattern:
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

def areMonitoredFilesChanged(zmMetaConf):
    """
    Detect that current monitored files are changed.
    """

    try:
        _hash = utils.hashFiles(zmMetaConf.monitfiles)
    except EnvironmentError:
        return True

    return _hash != zmMetaConf.monithash

def areToolchainEnvVarsAreChanged(zmMetaConf):
    """
    Detect that current toolchain env vars are changed.
    """

    lastEnvVars = zmMetaConf.toolenvs
    envVarNames = getAllToolchainEnvVarNames()
    for name in envVarNames:
        if name not in lastEnvVars:
            return True
        if lastEnvVars[name] != os.environ.get(name, ''):
            return True

    return False

def isBuildTypeConfigured(bconfManager):
    """
    Detect that data for current buildtype is configured.
    """

    rootbconf  = bconfManager.root
    buildtype  = rootbconf.selectedBuildType
    zmcachedir = rootbconf.confPaths.zmcachedir

    cachePath = makeTasksCachePath(zmcachedir, buildtype)
    if not db.exists(cachePath):
        return False

    return True

def needToConfigure(bconfManager, zmMetaConf):
    """
    Detect if it's needed to run 'configure' command
    """

    if zmMetaConf.zmversion != version.current():
        return True

    rootdir = bconfManager.root.rootdir
    if zmMetaConf.rundir != rootdir or zmMetaConf.platform != PLATFORM:
        return True

    if areMonitoredFilesChanged(zmMetaConf):
        return True

    if areToolchainEnvVarsAreChanged(zmMetaConf):
        return True

    if not isBuildTypeConfigured(bconfManager):
        return True

    return False

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
