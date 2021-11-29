# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import textwrap

from zm.autodict import AutoDict
from zm import cli
from zm.buildconf.processing import ConfManager
from zm.waf import wrappers
from zm.waf import launcher

SUBDIR_LVL1 = 'lib'
SUBDIR_LVL2 = 'core'

CONF_PARENT_YML = """

conditions:
  myenv:
    env:
      MYVAR: testvar

buildtypes:
  debug:
    %s

  default: debug

"""

CONF_PARENT_YML += """
subdirs: [ %s ]

""" % (SUBDIR_LVL1)

MIDDLE_SUBDIRS_YML = """
subdirs: [ %s ]
""" % SUBDIR_LVL2

CONF_CHILD_YML = """

tasks:
  util :
    features : cxxshlib
    source   : 'shlib/**/*.cpp'

  prog :
    features : cxxprogram
    source   : 'prog/**/*.cpp'
    use      : util

buildtypes:
  debug :
    %s
"""

def makeParamText(text):
    text = textwrap.dedent(text)
    text = textwrap.indent(text, ' ' * 4)
    return text

def _checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams, expected):

    wrappers.setUp()

    clivars = { 'buildtype': 'debug' }

    rootDir = tmpdir.mkdir("test")
    confFile = rootDir.join("buildconf.yml")
    body = CONF_PARENT_YML % makeParamText(textParams[0])

    confFile.write(body)

    lvl1Dir = rootDir.mkdir(SUBDIR_LVL1)
    confFile2 = lvl1Dir.join("buildconf.yml")
    confFile2.write(MIDDLE_SUBDIRS_YML)

    lvl2Dir = lvl1Dir.mkdir(SUBDIR_LVL2)
    confFile3 = lvl2Dir.join("buildconf.yml")
    body = CONF_CHILD_YML % makeParamText(textParams[1])
    confFile3.write(body)

    bconfManager = ConfManager(str(rootDir.realpath()), clivars = clivars)
    setattr(cfgctx, 'bconfManager', bconfManager)

    clicmd = cli.ParsedCommand(
        name = 'configure',
        args = AutoDict(buildtype = None),
        notparsed = [],
        orig = []
    )

    monkeypatch.setattr(cli, 'selected', clicmd)

    launcher.loadFeatureModules(bconfManager)
    launcher.setWafMainModule(bconfManager.root.rootdir)
    cfgctx.execute()

    for taskName in ('util', 'prog'):
        assert cfgctx.allTasks[taskName]['cxxflags'] == expected

def checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch,
                                            textParams, expected1, expected2):

    monkeypatch.setenv('MYVAR', 'none')
    _checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch,
                                      textParams, expected1)

    monkeypatch.setenv('MYVAR', 'testvar')
    tmpdir = tmpdir.mkdir("2")
    _checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch,
                                      textParams, expected2)

def testSubdirsBuildtypesSelectParam1(cfgctx, tmpdir, monkeypatch):

    textParams = [
      """
      cxxflags.select:
        default : -O0 -g
        myenv   : -O0 -Wextra
      """,

      """
      cxxflags.select:
        default : -O1 -g
        myenv   : -O1 -Wextra
      """
    ]

    checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams,
                                      ['-O1', '-g'], ['-O1', '-Wextra'])

def testSubdirsBuildtypesSelectParam2(cfgctx, tmpdir, monkeypatch):

    textParams = [
      """
      cxxflags: -O2
      cxxflags.select:
        default : -O0 -g
        myenv   : -O0 -Wextra
      """,

      """
      cxxflags: -O3
      cxxflags.select:
        default : -O1 -g
        myenv   : -O1 -Wextra
      """
    ]

    checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams,
                                      ['-O1', '-g'], ['-O1', '-Wextra'])

def testSubdirsBuildtypesSelectParam3(cfgctx, tmpdir, monkeypatch):

    textParams = [
      """
      cxxflags.select:
        default : -O0 -g
        myenv   : -O0 -Wextra
      """,

      """
      cxxflags: -O3 -fPIC
      cxxflags.select:
        myenv   : -O1 -Wextra
      """
    ]

    checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams,
                                      ['-O3', '-fPIC'], ['-O1', '-Wextra'])

def testSubdirsBuildtypesSelectParam4(cfgctx, tmpdir, monkeypatch):

    textParams = [
      """
      cxxflags.select:
        default : -O0 -g
        myenv   : -O0 -Wextra
      """,

      """
      cxxflags.select:
        myenv   : -O1 -Wextra
      """
    ]

    checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams,
                                      ['-O0', '-g'], ['-O1', '-Wextra'])

def testSubdirsBuildtypesSelectParam5(cfgctx, tmpdir, monkeypatch):

    textParams = [
      """
      cxxflags.select:
        default : -O0 -g
        myenv   : -O0 -Wextra
      """,

      """
      cxxflags: -O1 -Wextra
      """
    ]

    checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams,
                                      ['-O1', '-Wextra'], ['-O1', '-Wextra'])

def testSubdirsBuildtypesSelectParam6(cfgctx, tmpdir, monkeypatch):

    textParams = [
      """
      cxxflags: -O1 -Wextra
      """,

      """
      cxxflags.select:
        default : -O0 -g
        myenv   : -O0 -Wextra
      """,
    ]

    checkSubdirsBuildtypesSelectParam(cfgctx, tmpdir, monkeypatch, textParams,
                                      ['-O0', '-g'], ['-O0', '-Wextra'])
