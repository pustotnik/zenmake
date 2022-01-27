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

from waflib import Errors as waferror, Options
from waflib.Task import Task
from waflib.TaskGen import feature, before, after
from waflib.Tools import qt5
from zm.constants import PLATFORM
from zm import error, utils, cli
from zm.features import precmd, postcmd
from zm.pathutils import getNativePath, getNodesFromPathsConf
from zm.waf.assist import allowTGenAttrs
from zm.waf.taskgen import isolateExtHandler

_relpath = os.path.relpath
_commonpath = os.path.commonpath

# Allow the 'moc' param for Waf taskgen instances
allowTGenAttrs(['moc'])

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

def _configureQt5(conf):
    """
    Alternative version of 'configure' from waflib.Tools.qt5
    The main reason is to use more optimal order of compiler flags
    in the checks to speed up configuration.
    """

    conf.find_qt5_binaries()
    conf.set_qt5_libs_dir()
    conf.set_qt5_libs_to_check()
    conf.set_qt5_defines()
    conf.find_qt5_libraries()
    conf.add_qt5_rpath()
    conf.simplify_qt5_libs()

    # python module xml.sax exists since python 2.0 so we don't check qt5.has_xml

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

def _configureQt5ForTask(conf, taskParams, taskEnvs):

    conf.variant = taskVariant = taskParams['$task.variant']
    taskEnv = conf.env
    rootEnv = conf.all_envs['']
    assert taskEnv.parent == rootEnv

    taskEnv.parent = None # we don't need keys from root env
    envKeys = sorted(x for x in taskEnv.keys() if x != 'undo_stack')
    envId = utils.hashOrdObj([(k, taskEnv[k]) for k in envKeys])
    taskEnv.parent = rootEnv

    readyEnv = taskEnvs.get(envId)
    if readyEnv is not None:
        readyEnv.parent = None # don't copy root env
        newEnv = utils.deepcopyEnv(readyEnv)
        newEnv.parent = readyEnv.parent = rootEnv
        conf.all_envs[taskVariant] = newEnv
        return

    _configureQt5(conf)

    taskEnvs[envId] = taskEnv

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
        if not any(x.upper() == 'QT5CORE' for x in deps):
            # 'Qt5Core' must be always in deps
            deps.insert(0, 'Qt5Core')
        qtLibNames.extend([x for x in deps if x.startswith('Qt5')])

        taskParams['use'] = deps
        qtTasks.append(taskParams)

    # speed up: set the list of libraries to be requested via pkg-config/pkgconf
    qtLibNames = utils.uniqueListWithOrder(qtLibNames)
    conf.qt5_vars = qtLibNames

    qtTaskEnvs = {}
    for taskParams in qtTasks:
        _configureQt5ForTask(conf, taskParams, qtTaskEnvs)

    # switch current env to the root env
    conf.variant = ''

@feature('qt5')
@before('process_use')
def adjuctQt5UseNames(tgen):
    """
    ZenMake uses Qt5 lib names in the original title case.
    Waf wants Qt5 lib names in 'use' in uppercase.
    """

    deps = utils.toList(getattr(tgen, 'use', []))
    deps = [x.upper() if x.upper().startswith('QT5') else x for x in deps]
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
