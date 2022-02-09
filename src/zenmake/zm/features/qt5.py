# coding=utf-8
#

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Qt5 support, derived/based on the qt5 module from Waf.

 About MOC: according to the Qt5 documentation:
 C++ classes with Q_OBJECT are declared in foo.h:
    - put foo.h as a header to the 'moc' tool
    - add the resulting moc_foo.cpp to the source files
 C++ classes with Q_OBJECT are declared in foo.cpp:
    - add #include "foo.moc" at the end of foo.cpp
"""

import os
import re

from waflib import Errors as waferror
from waflib.Task import Task
from waflib.TaskGen import feature, before, after
from waflib.Tools import qt5
from zm.constants import PLATFORM, HOST_OS
from zm import error, utils
from zm.features import precmd, postcmd
from zm.pathutils import getNativePath, getNodesFromPathsConf
from zm.waf import assist
from zm.waf.taskgen import isolateExtHandler

_joinpath   = os.path.join
_pathexists = os.path.exists
_isdir      = os.path.isdir
_relpath    = os.path.relpath
_commonpath = os.path.commonpath

# Allow the 'moc' param for Waf taskgen instances
assist.allowTGenAttrs(['moc'])

# Isolate existing extension handlers to avoid conflicts with other tools
# and to avoid use of tools in tasks where these tools are inappropriate.
isolateExtHandler(qt5.cxx_hook, qt5.EXT_QT5, 'qt5')
isolateExtHandler(qt5.create_rcc_task, qt5.EXT_RCC, 'qt5')
isolateExtHandler(qt5.create_uic_task, qt5.EXT_UI, 'qt5')
isolateExtHandler(qt5.add_lang, ['.ts'], 'qt5')

QRC_BODY_TEMPL = """<!DOCTYPE RCC><RCC version="1.0">
<qresource prefix="%s">
%s
</qresource>
</RCC>
"""

QRC_LINE_TEMPL = """    <file alias="%s">%s</file>"""

EXTRA_PKG_CONFIG_PATHS = (
    '/usr/lib/qt5/lib/pkgconfig',
    '/opt/qt5/lib/pkgconfig',
    '/usr/lib/qt5/lib',
    '/opt/qt5/lib',
)

QT5_SYSENV_VARS = (
    'QT5_BINDIR', 'QT5_LIBDIR', 'QT5_INCLUDES',
    'QT5_NO_PKGCONF', 'QT5_FORCE_STATIC',
    'QT5_SEARCH_ROOT',
)

QMAKE_NAMES = ('qmake', 'qmake-qt5', 'qmake5')

_RE_QTINCL_DEPS = re.compile(r"^\s*#include\s*[<\"]([^<\"]+)/([^<\"]+)[>\"]\s*$")
_RE_QCONFIG_PRI = re.compile(r"^\s*([\w\d\.\_]+)\s*=\s*([\w\d\.\_]+)\s*$")

def _wrapMonEnvVarGetter(origFunc):
    def execute():
        return origFunc() + QT5_SYSENV_VARS
    execute.__doc__ = origFunc.__doc__
    return execute

assist.getMonitoredEnvVarNames = _wrapMonEnvVarGetter(assist.getMonitoredEnvVarNames)

def toQt5Name(name):
    """ Convert name from QtSomeName to Qt5SomeName """

    if name.startswith('Qt') and name[2] != '5':
        return '%s5%s' % (name[:2], name[2:])
    return name

def queryQmake(conf, qmake, prop):
    """ Run qmake -query prop and return result """
    if not isinstance(qmake, list):
        qmake = [qmake]
    return conf.cmd_and_log(qmake + ['-query', prop]).strip()

@postcmd('init')
def postInit(_):
    """ Extra init after wscript.init """

    # Prevent impact on Waf code
    os.environ.pop('QT5_BIN', None)  # ZenMake provides QT5_BINDIR instead of QT5_BIN
    os.environ.pop('QT5_ROOT', None) # ZenMake does not provide this variable

    # adjust QT5_BINDIR to Waf code
    qtbindir = os.environ.get('QT5_BINDIR')
    if qtbindir:
        os.environ['QT5_BIN'] = qtbindir
        # Waf ignores QT5_BIN if QT5_ROOT is not set or empty (bug?)
        os.environ['QT5_ROOT'] = os.path.normpath(_joinpath(qtbindir, os.pardir))

def _checkQtIsSuitable(conf, qmake, expectedMajorVer = '5'):

    try:
        qtver = queryQmake(conf, qmake, 'QT_VERSION')
    except waferror.WafError:
        return None

    majorVer = qtver.split('.')[0]
    if majorVer != expectedMajorVer:
        return None

    qtlibdir = queryQmake(conf, qmake, 'QT_INSTALL_LIBS')
    dotLibExists = _pathexists(_joinpath(qtlibdir, 'Qt5Core.lib'))
    isMSVC = conf.env.CXX_NAME == 'msvc'
    if (isMSVC and not dotLibExists) or (not isMSVC and dotLibExists):
        return None

    def checkQtArchSoftly(qmake):

        qtdatadir = queryQmake(conf, qmake, 'QT_HOST_DATA')
        destArch = utils.toPosixArchName(conf.env.DEST_CPU)

        filepath = _joinpath(qtdatadir, 'mkspecs', 'qconfig.pri')
        if not _pathexists(filepath):
            # Just ignore checking if the file not found
            return True

        with open(filepath, 'r') as file:
            for line in file.readlines():
                matchObj = _RE_QCONFIG_PRI.match(line)
                if not matchObj:
                    continue
                name, value = matchObj.group(1), matchObj.group(2)
                if name == 'QT_ARCH':
                    if destArch != value:
                        return False
                    break
            else:
                # QT_ARCH not found, invalid qconfig.pri?
                return False

        return True

    if not checkQtArchSoftly(qmake):
        return None

    return qtver

def _tryToFindQt5(conf):

    sysenv = conf.environ

    if sysenv.get('QT5_BIN'):
        return

    searchdir = sysenv.get('QT5_SEARCH_ROOT')
    if searchdir and not _isdir(searchdir):
        msg = 'The %r directory from QT5_SEARCH_ROOT does not exist.' % searchdir
        conf.fatal(msg)

    if not searchdir:
        if PLATFORM == 'windows':
            searchdir = 'C:\\Qt'
            if not _isdir(searchdir):
                return
        else:
            return

    qmakeFNames = QMAKE_NAMES
    if HOST_OS == 'windows':
        qmakeFNames = [x + '.exe' for x in QMAKE_NAMES]

    foundQt = []
    for dirpath, _, filenames in os.walk(searchdir):
        filenames = set(filenames)
        found = next((x for x in qmakeFNames if x in filenames), None)
        if not found:
            continue

        qmake = dirpath + os.sep + found
        qtver = _checkQtIsSuitable(conf, qmake)
        if qtver:
            foundQt.append((dirpath, qtver))

    def getHighestQtVerDir(foundQt):
        if len(foundQt) == 1:
            return foundQt[0][0]

        result = {}
        for dirpath, qtver in foundQt:
            qtver = tuple(int(x) for x in qtver.split('.'))
            result[qtver] = dirpath

        return result[sorted(result.keys())[-1]]

    if foundQt:
        paths = sysenv.get('PATH', '').split(os.pathsep)
        paths.insert(0, getHighestQtVerDir(foundQt))
        sysenv['PATH'] = os.pathsep.join(paths)

def _findQt5LibsWithPkgConf(conf, forceStatic):

    env    = conf.env
    sysenv = conf.environ
    qtlibs = env.QTLIBS

    pkgCfgPaths = [qtlibs, '%s/pkgconfig' % qtlibs, *EXTRA_PKG_CONFIG_PATHS]
    pkgCfgEnvPath = sysenv.get('PKG_CONFIG_PATH', '')
    if pkgCfgEnvPath:
        pkgCfgPaths.insert(0, pkgCfgEnvPath)
    pkgCfgPaths = ':'.join(pkgCfgPaths)

    kwargs = dict(
        args = '--cflags --libs',
        mandatory = False, force_static = forceStatic,
        pkg_config_path = pkgCfgPaths
    )

    for name in conf.qt5_vars:
        conf.check_cfg(package = name, **kwargs)

def _gatherQt5LibDepsFromHeaders(conf, qtIncludes):
    """
    Find Qt lib deps from *.Depends Qt headers
    It's not perfect but better than nothing.
    """

    def readModulesFromFile(filepath):
        modules = []
        if not _pathexists(filepath):
            return modules
        with open(filepath, 'r') as file:
            for line in file.readlines():
                matchObj = _RE_QTINCL_DEPS.match(line)
                if matchObj:
                    qtmodname = matchObj.group(1)
                    modules.append(qtmodname)
        return utils.uniqueListWithOrder(modules)

    def gatherModules(modules, seen):

        result = []
        for module in modules:
            if module in seen:
                continue

            seen.add(module)
            result.append(module)

            filepath = _joinpath(qtIncludes, module, '%sDepends' % module)
            result.extend(gatherModules(readModulesFromFile(filepath), seen))

        return result

    deps = {}
    for libname in conf.qt5_vars:
        seen = set()
        module = libname.replace('Qt5', 'Qt', 1)
        deps[libname] = gatherModules([module], seen)

    return deps

def _findSingleQt5LibAsIs(conf, qtlibname, qtlibDeps, forceStatic):

    env      = conf.env
    qtLibDir = env.QTLIBS
    uselib   = qtlibname.upper()

    if forceStatic:
        exts   = ('.a', '.lib')
        envPrefix = 'STLIB'
    else:
        exts   = ('.so', '.lib')
        envPrefix = 'LIB'

    def libPrefixExt():
        for ext in exts:
            for prefix in ('lib', ''):
                yield (prefix, ext)

    def addModuleDefine(module):
        defname = 'QT_%s_LIB' % module[2:].upper()
        env.append_unique('DEFINES_%s' % uselib, defname)

    def setUpLib(prefix, module, ext):
        basename = toQt5Name(module)
        libFileName = prefix + basename + ext
        if not _pathexists(_joinpath(qtLibDir, libFileName)):
            return False

        libval = prefix + basename if env.DEST_OS == 'win32' else basename
        env.append_unique('%s_%s' % (envPrefix, uselib), libval)
        addModuleDefine(module)
        return True

    found = False
    for prefix, ext in libPrefixExt():
        for module in qtlibDeps[qtlibname]:
            if setUpLib(prefix, module, ext):
                found = True

        if found:
            env.append_unique('%sPATH_%s' % (envPrefix, uselib), qtLibDir)
            # fix for header-only modules
            addModuleDefine(qtlibDeps[qtlibname][0])
            return True

    return False

def _findQt5LibsAsIs(conf, forceStatic):

    env    = conf.env
    sysenv = conf.environ

    qtIncludes = sysenv.get('QT5_INCLUDES') or \
                        queryQmake(conf, env.QMAKE, 'QT_INSTALL_HEADERS')
    qtIncludes = getNativePath(qtIncludes)

    deps = _gatherQt5LibDepsFromHeaders(conf, qtIncludes)

    for qtlibname in conf.qt5_vars:
        uselib = qtlibname.upper()

        for depname in deps[qtlibname]:
            env.append_unique('INCLUDES_' + uselib, _joinpath(qtIncludes, depname))
        env.append_unique('INCLUDES_' + uselib, qtIncludes)

        if PLATFORM == 'darwin':
            fwkName = qtlibname.replace('Qt5', 'Qt', 1)
            fwkDir  = fwkName + '.framework'

            qtDynLib = _joinpath(env.QTLIBS, fwkDir, fwkName)
            if _pathexists(qtDynLib):
                env.append_unique('FRAMEWORK_' + uselib, fwkName)
                env.append_unique('FRAMEWORKPATH_' + uselib, env.QTLIBS)
                conf.msg('Checking for %s' % qtlibname, qtDynLib, 'GREEN')
            else:
                conf.msg('Checking for %s' % qtlibname, False, 'YELLOW')

            env.append_unique('INCLUDES_' + uselib,
                                _joinpath(env.QTLIBS, fwkDir, 'Headers'))
        else:
            result = _findSingleQt5LibAsIs(conf, qtlibname, deps, forceStatic)
            if not result and not forceStatic:
                result = _findSingleQt5LibAsIs(conf, qtlibname, deps, True)
            msgColor = 'GREEN' if result else 'YELLOW'
            conf.msg('Checking for %s' % qtlibname, result, msgColor)

def _findQt5Libs(conf):

    sysenv = conf.environ
    forceStatic = utils.envValToBool(sysenv.get('QT5_FORCE_STATIC'))
    noPkgConfig = utils.envValToBool(sysenv.get('QT5_NO_PKGCONF'))

    if not noPkgConfig:
        try:
            conf.check_cfg(atleast_pkgconfig_version = '0.1')
        except waferror.ConfigurationError:
            noPkgConfig = True

    if noPkgConfig:
        _findQt5LibsAsIs(conf, forceStatic)
    else:
        _findQt5LibsWithPkgConf(conf, forceStatic)

def _fixQtDefines(conf):

    env = conf.env
    hdefines = set()
    for name in conf.qt5_vars:
        defines = env['DEFINES_%s' % name.upper()]
        defines = [x[:-4] if x.endswith('_LIB') else x for x in defines]
        hdefines.update(['HAVE_%s' % x.replace('_', '5', 1) for x in defines])

    for name in hdefines:
        conf.define(name, 1, False)

def _detectQtRtLibPath(conf):
    env = conf.env
    qtCoreDynLibName = env.cxxshlib_PATTERN % 'Qt5Core'

    def getDirs():
        yield env.QTLIBS
        yield getNativePath(queryQmake(conf, env.QMAKE, 'QT_INSTALL_BINS'))

    rtLibPath = ''
    for path in getDirs():
        if _pathexists(_joinpath(path, qtCoreDynLibName)):
            rtLibPath = path
            break
    else:
        conf.fatal("Could not find Qt5 runtime library directory")

    conf.env['QT5_RT_LIBPATH'] = rtLibPath

def _configureQt5CmnEnv(conf):

    _tryToFindQt5(conf)

    qt5.find_qt5_binaries(conf)
    qt5.set_qt5_libs_dir(conf)

    _findQt5Libs(conf)
    _fixQtDefines(conf)

    qt5.simplify_qt5_libs(conf)

    _detectQtRtLibPath(conf)

def _detectQt5Flags(conf):

    codefrag = '#include <QMap>\nint main(int argc, char **argv)'\
               ' { QMap<int,int> m; return m.keys().size(); }\n'

    cxxName = conf.env.CXX_NAME
    if cxxName in ('gcc', 'clang'):
        # Starting with GCC5 the only option for Qt is -fPIC
        # https://lists.qt-project.org/pipermail/development/2015-May/021557.html
        flagsToTry = ['-fPIC', [], '-fPIE', '-std=c++11' ,
                    ['-std=c++11', '-fPIC'], ['-std=c++11', '-fPIE']]
    else:
        flagsToTry = [[], '-fPIC', '-fPIE', '-std=c++11' ,
                    ['-std=c++11', '-fPIE'], ['-std=c++11', '-fPIC']]

    for flags in flagsToTry:
        msg = 'See if Qt files compile'
        if flags:
            msg += ' with %s' % flags
        try:
            conf.check(features = 'qt5 cxx', use = 'Qt5Core', uselib_store = 'qt5',
                        cxxflags = flags, fragment = codefrag, msg = msg)
        except waferror.ConfigurationError:
            pass
        else:
            break
    else:
        conf.fatal('Could not build a simple Qt application')

    if PLATFORM == 'freebsd':
        kwargs = dict(
            features = 'qt5 cxx cxxprogram',
            use = 'Qt5Core', fragment = codefrag,
        )
        try:
            conf.check(msg='Can we link Qt programs on FreeBSD directly?', **kwargs)
        except waferror.ConfigurationError:
            conf.check(uselib_store='qt5', libpath='/usr/local/lib',
                        msg='Is /usr/local/lib required?', **kwargs)

def _configureQt5ForTask(conf, taskParams, sharedData):
    """
    Based on waflib.Tools.qt5.configure
    """

    conf.variant = taskVariant = taskParams['$task.variant']
    taskEnv = conf.env
    rootEnv = conf.all_envs['']
    assert taskEnv.parent == rootEnv

    taskEnv.parent = None # we don't need keys from root env
    envKeys = sorted(x for x in taskEnv.keys() if x != 'undo_stack')
    envId = utils.hashOrdObj([(k, taskEnv[k]) for k in envKeys])
    taskEnv.parent = rootEnv

    qt5CmnEnv = sharedData.get('qt-cmn-env')
    if qt5CmnEnv is None:

        qt5CmnEnv = taskEnv.derive()
        conf.env = qt5CmnEnv

        _configureQt5CmnEnv(conf)
        conf.env = taskEnv

        delattr(qt5CmnEnv, 'parent')
        sharedData['qt-cmn-env'] = qt5CmnEnv

    taskEnv.update(utils.deepcopyEnv(qt5CmnEnv))

    rtLibPaths = taskParams.setdefault('$rt-libpath', [])
    rtLibPaths.append(taskEnv['QT5_RT_LIBPATH'])

    readyEnv = sharedData.get(envId)
    if readyEnv is not None:
        readyEnv.parent = None # don't copy root env
        newEnv = utils.deepcopyEnv(readyEnv)
        newEnv.parent = readyEnv.parent = rootEnv
        conf.all_envs[taskVariant] = newEnv
        return

    sharedData[envId] = taskEnv
    _detectQt5Flags(conf)

# The 'after' and 'before' are not needed here, it is just for more stable
# work for the possible future.
@precmd('configure', after = ['cxx'], before = ['runcmd', 'test'])
def preConf(conf):
    """ Prepare task params before wscript.configure """

    qtLibNames = []
    qtTasks = []

    for taskParams in conf.allOrderedTasks:

        features = taskParams['features']

        if 'qt5' not in features:
            continue

        if 'cxx' not in features:
            msg = "Feature 'cxx' not found in the task %r." % taskParams['name']
            msg += " The 'qt5' feature can be used only in C++ tasks."
            raise error.ZenMakeConfError(msg, confpath = taskParams['$bconf'].path)

        # it is better to set 'qt5' in features at the first place
        features = ['qt5'] + [x for x in features if x != 'qt5']

        rclangname = taskParams.pop('rclangname', None)
        if rclangname is not None:
            taskParams['langname'] = rclangname

        deps = taskParams.get('use', [])
        deps = [ toQt5Name(x) for x in deps]
        if not any(x.upper() == 'QT5CORE' for x in deps):
            # 'Qt5Core' must be always in deps
            deps.insert(0, 'Qt5Core')
        qtLibNames.extend([x for x in deps if x.startswith('Qt5')])

        taskParams['use'] = deps
        qtTasks.append(taskParams)

    # set the list of qt modules/libraries
    conf.qt5_vars = utils.uniqueListWithOrder(qtLibNames)

    sharedData = {}
    for taskParams in qtTasks:
        _configureQt5ForTask(conf, taskParams, sharedData)

    # switch current env to the root env
    conf.variant = ''

@feature('qt5')
@before('process_use')
def adjustQt5UseNames(tgen):
    """
    ZenMake uses Qt5 lib/module names in the original title case.
    Waf wants Qt5 lib names in 'use' in uppercase.
    """

    deps = utils.toList(getattr(tgen, 'use', []))
    deps = [x.upper() if x.upper().startswith('QT') else x for x in deps]
    tgen.use = deps

@feature('qt5')
@after('process_source')
@before('apply_incpaths')
def addExtraMocIncludes(tgen):
    """
    Add includes for moc files
    """

    includes = utils.toList(getattr(tgen, 'includes', []))
    for task in tgen.compiled_tasks:
        node = task.inputs[0]
        if node.is_src(): # ignore dynamic inputs from tasks like the 'moc' task
            # The generated .moc files are always in the build directory
            includes.append(node.parent.get_bld())
    tgen.includes = utils.uniqueListWithOrder(includes)

@feature('qt5')
@before('process_source')
def process_mocs(tgen):
    """
    Processes MOC files included in headers.
    Wrapped version of waflib.Tools.qt5.process_mocs that adds ability
    to use complex paths in the same way as for the 'source' task param.
    """

    # pylint: disable = invalid-name

    moc = getattr(tgen, 'moc', [])
    if not moc:
        return

    bld = tgen.bld
    bconfManager = getattr(bld, 'bconfManager', None)

    if not bconfManager:
        # it's called from a config action
        qt5.process_mocs(tgen)
        return

    rootdir = bconfManager.root.rootdir
    taskParams = getattr(tgen, 'zm-task-params')

    startNode = bld.getStartDirNode(taskParams['$startdir'])
    moc = getNodesFromPathsConf(bld, moc, rootdir)
    # moc headers as 'includes' paths must be relative to the startdir
    moc = [x.path_from(startNode) for x in moc]
    tgen.moc = moc

    qt5.process_mocs(tgen)

def _checkQmPathUnique(tgen, qmpath, qmInfo):

    otherQm = qmInfo.get(qmpath)
    if otherQm is not None:
        msg = "Tasks '%s' and '%s'" % (tgen.name, otherQm['tgen-name'])
        msg += " have the same output .qm path:\n  %s" % qmpath
        msg += "\nUse the 'bld-langprefix'/'unique-qmpaths' task "
        msg += "parameters to fix it. Or don't use the same .ts files"
        msg += " in these tasks."
        raise error.ZenMakeError(msg)

def _createRcTranslTasks(tgen, qmTasks, rclangprefix):

    rcnode = 'rclang-%s' % tgen.name
    rcnode = tgen.path.find_or_declare('%s.%d.qrc' % (rcnode, tgen.idx))

    qmNodes = [x.outputs[0] for x in qmTasks]
    kwargs = { 'qrcprefix' : rclangprefix }
    qm2rccTask = tgen.create_task('qm2qrc', qmNodes, rcnode, **kwargs)
    rccTask = qt5.create_rcc_task(tgen, qm2rccTask.outputs[0])
    tgen.link_task.inputs.append(rccTask.outputs[0])

def _createQmInstallTasks(tgen, qmTasks, taskParams):

    bld = tgen.bld
    if not bld.is_install or not taskParams:
        return None

    qmNodes = [x.outputs[0] for x in qmTasks]

    destdir = taskParams.get('install-langdir')
    if destdir is None:
        destdir = '$(appdatadir)/translations'
        destdir = utils.substBuiltInVars(destdir, tgen.env['$builtin-vars'])
        destdir = os.path.normpath(getNativePath(destdir))

    taskParams = taskParams.copy()
    taskParams.pop('install-files', None)
    taskParams['install-files'] = [{
        'src' : [x.abspath() for x in qmNodes],
        'dst' : destdir,
        'do'  : 'copy'
    }]
    bld.setUpInstallFiles(taskParams)
    return destdir

def _createTranslTasks(tgen):

    tsFiles = getattr(tgen, 'lang', None)
    if not tsFiles:
        return

    zmTaskParams = getattr(tgen, 'zm-task-params', {})
    rclangprefix = zmTaskParams.get('rclangprefix')

    bld = tgen.bld
    btypeNode = bld.bldnode

    bconfManager = getattr(bld, 'bconfManager', None)
    if bconfManager is not None:
        btypeNode = bld.root.make_node(bconfManager.root.selectedBuildTypeDir)

    fnprefix = ''
    qmpathprefix = None
    langDirDefine = None
    if zmTaskParams:
        if zmTaskParams.get('unique-qmpaths', False) and rclangprefix is None:
            fnprefix = zmTaskParams['name'] + '_'
        qmpathprefix = getNativePath(zmTaskParams.get('bld-langprefix'))
        langDirDefine = zmTaskParams.get('langdir-defname')

    if qmpathprefix is None:
        qmpathprefix = '@translations'

    qmNodeDir = None
    if rclangprefix is None:
        qmNodeDir = btypeNode.find_or_declare(qmpathprefix)

    try:
        qmInfo = bld.qmInfo
    except AttributeError:
        qmInfo = bld.qmInfo = {}

    def getQmNode(snode):

        fname = snode.name
        extIdx = fname.rfind('.')
        fname = fname[:extIdx] if extIdx > 0 else fname
        fname = '%s%s%s' % (fnprefix, fname, '.qm')

        if qmNodeDir is not None:
            qmnode = qmNodeDir.find_or_declare(fname)
        else:
            qmnode = snode.change_ext('.%d.qm' % tgen.idx)

        qmpath = qmnode.abspath()
        # check if .qm paths are unique
        _checkQmPathUnique(tgen, qmpath, qmInfo)

        qmInfo[qmpath] = { 'tgen-name' : tgen.name, 'alies' : fname }

        return qmnode

    qmTasks = [tgen.create_task('ts2qm', x, getQmNode(x)) for x in tsFiles]

    if rclangprefix is None:
        qmdestdir = _createQmInstallTasks(tgen, qmTasks, zmTaskParams)
        if langDirDefine:
            if qmdestdir is None:
                qmdestdir = qmNodeDir.abspath()
            tgen.env.append_value('DEFINES', '%s="%s"' % (langDirDefine, qmdestdir))
    else:
        _createRcTranslTasks(tgen, qmTasks, rclangprefix)

@feature('qt5')
@after('apply_link')
def apply_qt5(tgen):
    """
    Alternative version of 'apply_qt5' from waflib.Tools.qt5
    The main reason is to change location and names of *.qm files
    """

    # pylint: disable = invalid-name

    # set up flags for moc, it can be important
    mocFlags = []
    env = tgen.env
    for flag in [x for x in utils.toListSimple(env.CXXFLAGS) if len(x) > 2]:
        if flag[:2] in ('-D', '-I', '/D', '/I'):
            if flag[0] == '/':
                flag = '-' + flag[1:]
            mocFlags.append(flag)
    env.append_value('MOC_FLAGS', mocFlags)

    # .ts -> .qm and other related tasks
    _createTranslTasks(tgen)

class qm2qrc(Task):
    """
    Generates ``.qrc`` files with ``.qm`` files
    """

    # pylint: disable = invalid-name

    color = 'BLUE'
    after = 'ts2qm'

    def run(self):
        """
        Create a qrc file with .qm file paths
        """

        qrcprefix = getattr(self, 'qrcprefix', '/')
        outnode = self.outputs[0]
        qmInfo = self.generator.bld.qmInfo

        def getAlies(node):
            return qmInfo[node.abspath()]['alies']

        lines = [(getAlies(x), x.path_from(outnode.parent)) for x in self.inputs]
        lines = '\n'.join([QRC_LINE_TEMPL % (alies, path) for (alies, path) in lines])

        body = QRC_BODY_TEMPL % (qrcprefix, lines)
        outnode.write(body)

    def keyword(self):
        return "Generating .qrc"

    def __str__(self):

        launchNode = self.generator.bld.launch_node()

        if len(self.inputs) == 1:
            node = self.inputs[0]
            return node.path_from(launchNode)

        # original string is too long

        inputs = [x.abspath() for x in self.inputs]
        cmnPath = _commonpath(inputs)
        startFrom = len(cmnPath) + 1
        inputTails = ', '.join([ x[startFrom:] for x in inputs ])
        cmnPath = _relpath(cmnPath, launchNode.abspath())

        return "%s: %s" % (cmnPath, inputTails)

# Set more understandable labels for some specific task runs
setattr(qt5.moc, 'keyword', lambda _: "Generating moc")
setattr(qt5.ts2qm, 'keyword', lambda _: "Generating .qm from")
