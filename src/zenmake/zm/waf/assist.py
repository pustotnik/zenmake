# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some functions specific to use with the Waf.
"""

import os
import re

from zm.constants import PLATFORM
from zm.pyutils import stringtype, _unicode, _encode
from zm.autodict import AutoDict as _AutoDict
from zm.pathutils import getNodesFromPathsConf
from zm.error import ZenMakeError, ZenMakeConfError
from zm.error import ZenMakePathNotFoundError, ZenMakeDirNotFoundError
from zm.features import TASK_TARGET_FEATURES_TO_LANG, TASK_TARGET_FEATURES
from zm.features import SUPPORTED_TASK_FEATURES
from zm.features import ToolchainVars, getLoadedFeatures
from zm import utils, log, version, toolchains, db

joinpath  = os.path.join
splitpath = os.path.split
normpath  = os.path.normpath
relpath   = os.path.relpath

toList       = utils.toList
toListSimple = utils.toListSimple

_getenv = os.environ.get

# These keys are not removed from waf task gen on 'build' step
# Such keys as '*flags' and 'defines' are set in task envs, so they
# don't need to be protected from removing from waf task gen.
_usedWafTaskKeys = set([
    'name', 'target', 'features', 'source', 'includes',
    'lib', 'libpath', 'monitlibs', 'stlib', 'stlibpath', 'monitstlibs',
    'rpath', 'use', 'vnum', 'idx', 'export_includes', 'export_defines',
    'install_path',
])

_RE_TASKVARIANT_NAME = re.compile(r'[^-\w.]', re.UNICODE)
_RE_EXT_AT_THE_END = re.compile(r'\.\w+$', re.UNICODE)

def registerUsedWafTaskKeys(keys):
    ''' Register used Waf task keys '''
    _usedWafTaskKeys.update(keys)

def unregisterUsedWafTaskKeys(keys):
    ''' Unregister used Waf task keys '''
    _usedWafTaskKeys.difference_update(keys)

def getUsedWafTaskKeys():
    ''' Get used Waf task keys '''
    return _usedWafTaskKeys

def getMonitoredEnvVarNames():
    ''' Get all monitored env vars to reconfigure on their change '''

    envVarNames = ToolchainVars.allSysFlagVars()
    envVarNames += ToolchainVars.allSysVarsToSetToolchain()
    envVarNames += ('BUILDROOT', 'DESTDIR', 'PREFIX', 'BINDIR', 'LIBDIR')

    return envVarNames

def getMonitoredCliArgNames():
    ''' Get all monitored CLI args to reconfigure on their change '''

    return ('prefix', 'bindir', 'libdir')

def writeZenMakeMetaFile(filePath, meta, prevZmMeta):
    """
    Write ZenMake meta file with some things like files
    monitored for changes.
    """

    zmMeta = _AutoDict()
    zmMeta.zmversion = version.current()
    zmMeta.platform = PLATFORM

    zmMeta.attrs = meta.attrs
    zmMeta.monitfiles = sorted(set(meta.monitfiles))
    zmMeta.monithash  = utils.hashFiles(zmMeta.monitfiles)

    from waflib import Context
    zmMeta.rundir = Context.run_dir
    zmMeta.topdir = Context.top_dir
    zmMeta.outdir = Context.out_dir

    zmMeta.eparams = {}
    if prevZmMeta is not None:
        zmMeta.eparams.update(prevZmMeta.eparams)
    eparams = zmMeta.eparams[meta.buildtype] = { 'envs' : {}, 'cliargs': {} }

    for name in meta.envvars:
        eparams['envs'][name] = _getenv(name, '')

    for name in getMonitoredCliArgNames():
        val = meta.cliargs.get(name)
        if val is not None:
            eparams['cliargs'][name] = val

    dbfile = db.PyDBFile(filePath, extension = '')
    dbfile.save(zmMeta)

def loadZenMakeMetaFile(filePath):
    """
    Load ZenMake common ConfigSet file. Return None if failed
    """

    dbfile = db.PyDBFile(filePath, extension = '')
    try:
        data = dbfile.load(asConfigSet = True)
    except EnvironmentError:
        return None

    return data

def makeTasksCachePath(zmcachedir, buildtype):
    """ Make file path of zenmake tasks cache file for selected buildtype"""
    name = "%s.tasks" % buildtype
    return joinpath(zmcachedir, name)

def makeTargetsCachePath(zmcachedir, buildtype):
    """ Make file path of zenmake targets cache file for selected buildtype"""
    name = "%s.targets" % buildtype
    return joinpath(zmcachedir, name)

def makeTaskVariantName(buildtype, taskName):
    """ Make 'variant' name for task """

    name = _unicode(taskName).strip().replace(' ', '_')
    name = '%s.%s' % (buildtype, _RE_TASKVARIANT_NAME.sub('.', name))
    return _encode(name)

def makeTargetRealName(target, targetKind, pattern, env, verNum):
    """
    Make real file/path name of the target
    """

    if targetKind is None:
        return target

    if not pattern:
        pattern = '%s'

    dirpath, name = splitpath(target)

    if verNum and targetKind.endswith('shlib'):
        if env.DEST_OS == 'openbsd':
            # https://www.openbsd.org/faq/ports/specialtopics.html
            # the library naming scheme: libfoo.so.major.minor
            nums = verNum.split('.')
            major = nums[0]
            minor = nums[1] if len(nums) >= 2 else 0
            pattern = '%s.%s.%s' % (pattern, major, minor)
        # This piece of code was copied from Waf but there is no standard
        # library naming scheme on Windows. So it was disabled.
        #elif env.DEST_BINFMT == 'pe':
        #    nums = verNum.split('.')
        #    # include the version in the dll file name
        #    name = '%s-%s' % (name, nums[0])

    target = pattern % name
    if dirpath:
        target = '%s%s%s' % (dirpath, os.sep, target)

    return target

def orderTasksByLocalDeps(tasks):
    """
    Make list of tasks ordered by local deps
    """

    def calcWeight(allTasks, taskParams):

        weight = taskParams.get('$weight')
        if weight is not None:
            return weight

        weight = 1
        depWeights = [0]
        for dep in taskParams.get('use', []):
            depTaskParams = allTasks.get(dep)
            if not depTaskParams:
                continue
            if id(depTaskParams) == id(taskParams):
                raise ZenMakeError('Dependency cycle was found in buildconf tasks!')

            depWeights.append(calcWeight(allTasks, depTaskParams))

        weight += max(depWeights)
        taskParams['$weight'] = weight
        return weight

    tasksList = list(tasks.values())
    for taskParams in tasksList:
        calcWeight(tasks, taskParams)

    # From python docs:
    # `key and reverse touch each element only once`.
    # `the key function is called exactly once for each input record.`
    # So $weight can be poped.
    tasksList.sort(key = lambda x: x.pop('$weight'))
    return tasksList

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
        val = taskParams.get(var.lower())
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
    for var, val in _gathered.items():
        # Waf has some usefull predefined env vars for some compilers
        # so here we add values, not replace them.

        # waf env + (bconf + toolchains + sys env)
        val = env[var] + val

        # remove duplicates: keep only last unique values in the list
        val = utils.uniqueListWithOrder(reversed(val))
        val.reverse()
        env[var] = val

def fixToolchainEnvVars(env, taskParams):
    """
    Fix some env vars for some toolchains like env.LIBPATH
    """

    # fix (st)libpath
    for paramName, envVar in (('libpath', 'LIBPATH'), ('stlibpath', 'STLIBPATH')):
        envLibPath = env[envVar]
        if envLibPath:
            # Some waf tools (see msvc, ifort) set up env.LIBPATH but it's wrong
            # behavior. Actually it's better to move them in 'uselib_feature'
            # env var but I was lazy.
            taskParams[paramName] = taskParams.get(paramName, []) + envLibPath
            del env[envVar]

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
        ('install-path', 'install_path'),
        ('objfile-index', 'idx'),

        # ZenMake doesn't use Waf 'export_includes' and 'export_defines' anymore
    )

    for zmKey, wafKey in nameMap:
        val = taskParams.pop(zmKey, None)
        if val is not None:
            taskParams[wafKey] = val

def detectTaskFeatures(taskParams):
    """
    Detect all features for task
    Param 'ctx' is used only if an alias exists in features.
    """

    features = toListSimple(taskParams.get('features', []))

    detected = [ TASK_TARGET_FEATURES_TO_LANG.get(x, '') for x in features ]
    features = detected + features

    if 'run' in taskParams:
        features.append('runcmd')

    features = utils.uniqueListWithOrder(features)
    if '' in features:
        features.remove('')
    taskParams['features'] = features

    return features

def validateTaskFeatures(taskParams):
    """
    Check all features are valid
    """

    features = taskParams['features']
    unknown = [x for x in features if x not in SUPPORTED_TASK_FEATURES]
    if unknown:
        if len(unknown) == 1:
            msg = "Feature %r in task %r is not supported." % \
                (unknown[0], taskParams['name'])
        else:
            msg = "Features '%s' in task %r are not supported." % \
                (', '.join(unknown), taskParams['name'])
        raise ZenMakeConfError(msg)

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
        paths = []
        param = taskParams.get(paramName)
        if param is not None:
            # Waf doesn't change 'libpath' relative to current ctx.path as for 'includes'.
            # So we use absolute paths here.
            paths = param.abspaths()

        if paths:
            taskParams[paramName] = utils.uniqueListWithOrder(paths)

def handleTaskIncludesParam(taskParams, startdir):
    """
    Make valid 'includes' for build task
    """

    # Includes paths must be relative to the startdir

    if 'includes' in taskParams:
        param = taskParams['includes']
        includes = param.relpaths(startdir)
    else:
        includes = []

    # The includes='.' add the startdir.
    # To save the same order with the Waf 'export_includes'
    # it's inserted in front of the list.
    includes.insert(0, '.')
    taskParams['includes'] = includes

def handleTaskSourceParam(ctx, taskParams):
    """
    Get valid 'source' for build task
    """

    src = taskParams.get('source')
    if not src:
        return []

    wspath = ctx.getStartDirNode(taskParams['$startdir'])
    bconf = ctx.getbconf(wspath)

    try:
        buildrootNode = ctx.brootNode
    except AttributeError:
        buildroot = bconf.confPaths.buildroot
        buildrootNode = ctx.root.make_node(buildroot)
        ctx.brootNode = buildrootNode

    def onNoPath(ex):
        if isinstance(ex, ZenMakeDirNotFoundError):
            msg = "Directory %r for the 'source' doesn't exist." % ex.path
            raise ZenMakeError(msg)
        if isinstance(ex, ZenMakePathNotFoundError):
            msg = "Error in the file %r:" % bconf.path
            msg += "\n  File %r from the 'source' not found." % ex.path
            raise ZenMakeError(msg)
        raise ex

    kwargs = {
        'cache' : taskParams.get('$cache-source', False),
        'excludeExtraPaths' : [buildrootNode],
        'onNoPath' : onNoPath,
    }

    return getNodesFromPathsConf(ctx, src, bconf.rootdir, **kwargs)

def checkWafTasksForFeatures(taskParams):
    """
    Validate current features with loaded Waf task classes
    """

    from waflib import Task

    # check only supported Waf features
    features = tuple(TASK_TARGET_FEATURES & set(taskParams['features']))
    for feature in features:
        if feature not in Task.classes:
            msg = "Feature %r cannot be processed for task %r." % \
                  (feature, taskParams['name'])
            msg += " Maybe you didn't set correct toolchain for this task."
            raise ZenMakeError(msg)

def doTotalCleanup(bconfPaths, verbose = 1):
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
    rootdir       = bconfPaths.rootdir

    assert not rootdir.startswith(buildroot)
    assert not rootdir.startswith(realbuildroot)

    paths = [realbuildroot, buildroot]
    for path in list(paths):
        paths.append(os.path.realpath(path))
    paths = list(set(paths))

    for path in paths:
        if os.path.isdir(path) and not os.path.islink(path):
            loginfo("Removing directory '%s'" % path)
            try:
                shutil.rmtree(path)
            except OSError as ex:
                raise ZenMakeError('Could not remove %r: %s' % (path, str(ex))) from ex

        if os.path.islink(path):
            loginfo("Removing symlink '%s'" % path)
            os.remove(path)

    from waflib import Options
    lockfile = os.path.join(rootdir, Options.lockfile)
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

    doTotalCleanup(bconfPaths, verbose)

def printZenMakeHeader(bconfManager):
    """
    Log header with some info.
    """

    bconf = bconfManager.root
    log.info("* Project name: '%s'" % bconf.projectName)
    if bconf.projectVersion:
        log.info("* Project version: %s" % bconf.projectVersion)
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

def areExternalParamsChanged(zmMetaConf, buildtype, cliargs):
    """
    Detect that monitored env vars or CLI args are changed.
    """

    if 'eparams' not in zmMetaConf:
        eparams = {}
    else:
        eparams = zmMetaConf.eparams.get(buildtype, {})

    prevEnvVars = eparams.get('envs', {})
    for name, val in prevEnvVars.items():
        if val != _getenv(name, ''):
            return True

    prevCliArgs = eparams.get('cliargs', {})
    for name in getMonitoredCliArgNames():
        if prevCliArgs.get(name) != cliargs.get(name):
            return True

    return False

def isBuildTypeConfigured(zmcachedir, buildtype):
    """
    Detect that data for current buildtype is configured.
    """

    cachePath = makeTasksCachePath(zmcachedir, buildtype)
    if not db.exists(cachePath):
        return False

    return True

def needToConfigure(zmMetaConf, rootdir, zmcachedir, buildtype, cliargs):
    """
    Detect if it's needed to run 'configure' command
    """

    if zmMetaConf.zmversion != version.current():
        return True

    if zmMetaConf.rundir != rootdir or zmMetaConf.platform != PLATFORM:
        return True

    if areMonitoredFilesChanged(zmMetaConf):
        return True

    if areExternalParamsChanged(zmMetaConf, buildtype, cliargs):
        return True

    if not isBuildTypeConfigured(zmcachedir, buildtype):
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
