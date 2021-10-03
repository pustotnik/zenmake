# coding=utf-8
#

# pylint: disable = missing-docstring

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import pytest

from zm.buildconf.processing import ConfManager

CONF_HEADER_YML = """

fragment1: |
    program
    end program

fragment2: |
    program
    $MYFLAGS
    end program

GCC_BASE_CXXFLAGS: -std=c++11 -fPIC
MYFLAGS: -O2 -g
MYFLAGS1: $MYFLAGS -Wall -Wextra
MYFLAGS2: -Wall $MYFLAGS -Wextra
MYFLAGS3: -Wall -Wextra $MYFLAGS
MYFLAGS4: ${MYFLAGS} -Wall -Wextra
MYFLAGS5: -Wall ${MYFLAGS} -Wextra
MYFLAGS6: -Wall -Wextra ${MYFLAGS}

AFLAGS1: $$GCC_BASE_CXXFLAGS -Wall ${MYFLAGS} -Wextra
AFLAGS2: "$GCC_BASE_CXXFLAGS -Wall $${MYFLAGS} -Wextra"
AFLAGS3: '$GCC_BASE_CXXFLAGS -Wall ${MYFLAGS} -Wextra'

"""

CONF_BODY_YML = """

buildtypes:
  debug1: { cxxflags: $MYFLAGS1 -O0 }
  debug2:
    cxxflags: ${MYFLAGS2} -O0
  debug3: { cxxflags: $$MYFLAGS3 -O0 }
  debug3:
    cxxflags: ${MYFLAGS3} -O0
  debug4: { cxxflags: "$MYFLAGS4 -O0" }
  debug5: { cxxflags: "${MYFLAGS5} -O0" }
  debug6: { cxxflags: '${MYFLAGS6} -O0' }

  release1 : { cxxflags: $AFLAGS1 -O2 }
  release2 : { cxxflags: $AFLAGS2 -O2 }
  release3 : { cxxflags: $AFLAGS3 -O2 }

tasks:
  util :
    features : cxxshlib
    source   : 'shlib/**/*.cpp'
    configure:
      - do: check-code
        text: $fragment1
        label: fragment1
      - do: check-code
        text: $fragment2
        label: fragment2

  prog :
    features : cxxprogram
    source   : 'prog/**/*.cpp'
    use      : util

"""

ROOT_CONF_YML = CONF_HEADER_YML + CONF_BODY_YML

SUBDIR_LVL1 = 'lib'
SUBDIR_LVL2 = 'core'
ROOT_SUBDIRS_YAML = """
%s
subdirs: [ %s ]

""" % (CONF_HEADER_YML, SUBDIR_LVL1)

MIDDLE_SUBDIRS_YML = """
subdirs: [ %s ]
""" % SUBDIR_LVL2

LAST_SUBDIRS_YAML = CONF_BODY_YML

def checkVars(bconf, dbgValidVals, relValidVals):

    buildtypes = bconf.getattr('buildtypes')[0]

    for idx in range(1, 7):
        buildtype = 'debug%d' % idx
        assert buildtypes[buildtype]['cxxflags'] == dbgValidVals[idx-1]

    for idx in range(1, 4):
        buildtype = 'release%d' % idx
        assert buildtypes[buildtype]['cxxflags'] == relValidVals[idx-1]

def checkConfigNoEnv(bconf):

    dbgValidVals = [
        "-O2 -g -Wall -Wextra -O0",
        "-Wall -O2 -g -Wextra -O0",
        "-Wall -Wextra -O2 -g -O0",
        "-O2 -g -Wall -Wextra -O0",
        "-Wall -O2 -g -Wextra -O0",
        "-Wall -Wextra -O2 -g -O0",
    ]

    relValidVals = [
        "-std=c++11 -fPIC -Wall -O2 -g -Wextra -O2",
        "-std=c++11 -fPIC -Wall -O2 -g -Wextra -O2",
        "-std=c++11 -fPIC -Wall -O2 -g -Wextra -O2",
    ]

    checkVars(bconf, dbgValidVals, relValidVals)

    assert bconf.tasks['util']['configure'][0]['text'] == "program\nend program\n"
    assert bconf.tasks['util']['configure'][1]['text'] == "program\n-O2 -g\nend program\n"

def checkConfigWithEnv(bconf):

    dbgValidVals = [
        "-O3 -Wall -Wall -Wextra -O0",
        "-Wall -O3 -Wall -Wextra -O0",
        "-O1 -Wall -Wextra -O0",
        "-O3 -Wall -Wall -Wextra -O0",
        "-Wall -O3 -Wall -Wextra -O0",
        "-Wall -Wextra -O3 -Wall -O0",
    ]

    relValidVals = [
        "-std=c++11 -fPIC -Wall -O3 -Wall -Wextra -O2",
        "-std=c++11 -fPIC -Wall -O2 -g -Wextra -O2",
        "-std=c++11 -fPIC -Wall -O3 -Wall -Wextra -O2",
    ]

    checkVars(bconf, dbgValidVals, relValidVals)

@pytest.mark.usefixtures("unsetEnviron")
def testBasic(tmpdir, monkeypatch):

    clivars = { 'buildtype': 'debug1' }

    rootDir = tmpdir.mkdir("test")
    confFile = rootDir.join("buildconf.yml")
    confFile.write(ROOT_CONF_YML)

    bconfManager = ConfManager(str(rootDir.realpath()), clivars = clivars)
    bconf = bconfManager.root

    checkConfigNoEnv(bconf)

    ##########################
    # with env
    monkeypatch.setenv('MYFLAGS', '-O3 -Wall')
    monkeypatch.setenv('MYFLAGS3', '-O1 -Wall -Wextra')

    bconfManager = ConfManager(str(rootDir.realpath()), clivars = clivars)
    bconf = bconfManager.root

    checkConfigWithEnv(bconf)

@pytest.mark.usefixtures("unsetEnviron")
def testSubdirs(tmpdir, monkeypatch):

    clivars = { 'buildtype': 'debug1' }

    rootDir = tmpdir.mkdir("test")
    confFile1 = rootDir.join("buildconf.yml")
    confFile1.write(ROOT_SUBDIRS_YAML)

    lvl1Dir = rootDir.mkdir(SUBDIR_LVL1)
    confFile2 = lvl1Dir.join("buildconf.yml")
    confFile2.write(MIDDLE_SUBDIRS_YML)

    lvl2Dir = lvl1Dir.mkdir(SUBDIR_LVL2)
    confFile3 = lvl2Dir.join("buildconf.yml")
    confFile3.write(LAST_SUBDIRS_YAML)

    bconfManager = ConfManager(str(rootDir.realpath()), clivars = clivars)
    bconf = bconfManager.configs[-1]

    checkConfigNoEnv(bconf)

    ##########################
    # with env
    monkeypatch.setenv('MYFLAGS', '-O3 -Wall')
    monkeypatch.setenv('MYFLAGS3', '-O1 -Wall -Wextra')

    bconfManager = ConfManager(str(rootDir.realpath()), clivars = clivars)
    bconf = bconfManager.configs[-1]

    checkConfigWithEnv(bconf)
