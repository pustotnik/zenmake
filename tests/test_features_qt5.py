# coding=utf-8
#

# pylint: disable = missing-docstring, invalid-name
# pylint: disable = too-many-statements

"""
 Copyright (c) 2022, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from waflib import Context
from waflib.ConfigSet import ConfigSet
from zm.autodict import AutoDict
from zm.utils import loadPyModule
from zm import features

joinpath = os.path.join

_local = {}

def _getQt5Module():

    module = _local.get('qt5')
    if module is None:
        task = AutoDict()
        task.features = ['cxxshlib', 'qt5']
        tasksList = [ {'test': task} ]
        features.loadFeatures(tasksList)

        module = _local['qt5'] = loadPyModule('zm.features.qt5', withImport = True)

    return module

def testAdjuctQt5UseNames():

    qt5 = _getQt5Module()
    tgen = AutoDict()
    tgen.use = 'tool Qt5Widgets qutil util'

    qt5.adjuctQt5UseNames(tgen)
    assert tgen.use == ['tool', 'QT5WIDGETS', 'qutil', 'util']

def testAddExtraMocIncludes(tmpdir):

    rootdir = tmpdir.mkdir("zm")
    srcroot = rootdir.mkdir("src")
    bldroot = rootdir.mkdir("build")

    ctx = Context.Context(run_dir = str(rootdir))
    ctx.srcnode = ctx.root.make_node(str(srcroot))
    ctx.bldnode = ctx.root.make_node(str(bldroot))

    tgen = AutoDict()
    tgen.includes = '. inc'

    task = AutoDict()
    task.inputs = [ctx.srcnode.make_node(joinpath('incs', 'test.h'))]
    tgen.compiled_tasks = [task]

    qt5 = _getQt5Module()
    qt5.addExtraMocIncludes(tgen)

    includes = [x if isinstance(x, str) else x.abspath() for x in tgen.includes]

    assert includes == [
        '.', 'inc',
        ctx.bldnode.make_node('incs').abspath()
    ]

def testApplyQt5(tmpdir):

    qt5 = _getQt5Module()

    buildWorkDirName = '@bld'

    rootdir = tmpdir.mkdir("prj")
    srcroot = rootdir.mkdir("src")
    bldroot = rootdir.mkdir("build")
    bldout  = bldroot.mkdir("debug")
    bldout = str(bldout)

    ctx = Context.Context(run_dir = str(rootdir))
    ctx.buildWorkDirName = buildWorkDirName

    makeNode = ctx.root.make_node
    ctx.srcnode = makeNode(str(srcroot))
    ctx.bldnode = makeNode(joinpath(bldout, buildWorkDirName))
    ctx.bldnode.mkdir()

    def makeBldNode(*args):
        return makeNode(joinpath(bldout, *args))

    tgen = AutoDict()
    tgen.idx = 2
    tgen.name = 'mytest'
    tgen.env = ConfigSet()
    tgen.env.CXXFLAGS = []
    tgen.path = ctx.srcnode
    tgen.link_task.inputs = []
    tgen.compiled_tasks = []

    tgen.bld = ctx
    bconfManager = AutoDict()
    bconfManager.root.selectedBuildTypeDir = bldout
    tgen.bld.bconfManager = bconfManager

    tsFiles = [
        joinpath(srcroot, 'lang_en.ts'),
        joinpath(srcroot, 'lang_nl.ts'),
    ]
    tsFiles = [ makeNode(x) for x in tsFiles ]
    tgen.lang = tsFiles

    createdTasks = []
    def createTaskEmu(name, src = None, tgt = None, **kwargs):
        createdTasks.append([name, src, tgt, kwargs])
        task = AutoDict()
        task.outputs = [ tgt ]
        return task

    tgen.create_task = createTaskEmu

    ### CASE: regular translations files
    tgen['zm-task-params'] = {
        'name' : tgen.name,
    }

    createdTasks.clear()
    qt5.apply_qt5(tgen)

    assert createdTasks == [
        ['ts2qm', tsFiles[0], makeBldNode('lang_en.qm'), {}],
        ['ts2qm', tsFiles[1], makeBldNode('lang_nl.qm'), {}],
    ]

    ### CASE: regular translations files with custom prefix
    tgen['zm-task-params'] = {
        'name' : tgen.name,
        'qmpathprefix' : 'tt/lang',
    }

    createdTasks.clear()
    qt5.apply_qt5(tgen)

    assert createdTasks == [
        ['ts2qm', tsFiles[0], makeBldNode('tt', 'lang', 'lang_en.qm'), {}],
        ['ts2qm', tsFiles[1], makeBldNode('tt', 'lang', 'lang_nl.qm'), {}],
    ]

    ### CASE: regular translations files with 'unique-qmpaths'
    tgen['zm-task-params'] = {
        'name' : tgen.name,
        'unique-qmpaths' : True,
    }

    createdTasks.clear()
    qt5.apply_qt5(tgen)

    assert createdTasks == [
        ['ts2qm', tsFiles[0], makeBldNode('%s_%s' % (tgen.name,'lang_en.qm')), {}],
        ['ts2qm', tsFiles[1], makeBldNode('%s_%s' % (tgen.name,'lang_nl.qm')), {}],
    ]

    ### CASE: translations files within resource file
    tgen['zm-task-params'] = {
        'name' : tgen.name,
        'rclangprefix' : 'lang',
    }

    createdTasks.clear()
    qt5.apply_qt5(tgen)

    qmNodes = [
        makeBldNode(buildWorkDirName, 'lang_en.2.qm'),
        makeBldNode(buildWorkDirName, 'lang_nl.2.qm')
    ]
    qrcNode = makeBldNode(buildWorkDirName, 'rclang-%s.%d.qrc' % (tgen.name, 2))
    cxxNode = makeBldNode(buildWorkDirName, 'rclang-%s.%d_rc.%d.cpp' % (tgen.name, 2, 2))
    assert len(createdTasks) == 5
    assert createdTasks[0] == ['ts2qm', tsFiles[0], qmNodes[0], {}]
    assert createdTasks[1] == ['ts2qm', tsFiles[1], qmNodes[1], {}]
    assert createdTasks[2] == ['qm2qrc', qmNodes, qrcNode, {'qrcprefix': 'lang'}]
    assert createdTasks[3] == ['rcc', qrcNode, cxxNode, {}]
    assert createdTasks[4] == ['cxx', cxxNode, cxxNode.change_ext('.o'), {}]
