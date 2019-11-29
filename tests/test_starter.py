# coding=utf-8
#

# _pylint: skip-file
# pylint: disable = wildcard-import, unused-wildcard-import, unused-import
# pylint: disable = missing-docstring, invalid-name, bad-continuation

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import pytest
import tests.common as cmn
from zm.autodict import AutoDict
from zm.constants import APPNAME
from zm import cli
from zm import starter

joinpath = os.path.join

def testHandleCLI(capsys):

    noBuildConf = True
    args = [APPNAME]
    options = {}

    with pytest.raises(SystemExit):
        starter.handleCLI(args, noBuildConf, options)
    # clean output
    capsys.readouterr()

    with pytest.raises(SystemExit):
        starter.handleCLI(args, noBuildConf, None)
    # clean output
    capsys.readouterr()

    #############
    args = [APPNAME, 'build']
    options = {}
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, options)
    assert cmd == cli.selected
    assert cmd.name == 'build'
    assert wafCmdLine[0] == 'build'
    assert cmd.args.verbose == 0
    assert cmd.args.jobs is None
    assert not cmd.args.progress

    options = {
        'verbose': 1,
        'jobs' : { 'build' : 4 },
        'progress' : {'any': False, 'build': True },
    }
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, options)
    assert cmd == cli.selected
    assert cmd.name == 'build'
    assert wafCmdLine[0] == 'build'
    assert cmd.args.verbose == 1
    assert cmd.args.jobs == 4
    assert cmd.args.progress
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, None)
    assert cmd == cli.selected
    assert cmd.name == 'build'
    assert wafCmdLine[0] == 'build'
    assert cmd.args.verbose == 0
    assert cmd.args.jobs is None
    assert not cmd.args.progress

    args = [APPNAME, 'test']
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, options)
    assert cmd == cli.selected
    assert cmd.name == 'test'
    assert wafCmdLine[0] == 'build'
    assert cmd.args.verbose == 1
    assert cmd.args.jobs is None
    assert not cmd.args.progress

def testFindTopLevelBuildConfDir(tmpdir):

    startdir = str(tmpdir.realpath())
    assert starter.findTopLevelBuildConfDir(startdir) is None

    dir1 = tmpdir.mkdir("dir1")
    dir2 = dir1.mkdir("dir2")
    dir3 = dir2.mkdir("dir3")
    dir4 = dir3.mkdir("dir4")

    assert starter.findTopLevelBuildConfDir(str(dir4)) is None

    buildconf = joinpath(str(dir4), 'buildconf.py')
    with open(buildconf, 'w+') as file:
        file.write("buildconf")
    assert starter.findTopLevelBuildConfDir(str(dir4)) == str(dir4)
    assert starter.findTopLevelBuildConfDir(str(dir3)) is None

    buildconf = joinpath(str(dir3), 'buildconf.yaml')
    with open(buildconf, 'w+') as file:
        file.write("buildconf")
    assert starter.findTopLevelBuildConfDir(str(dir4)) == str(dir3)
    assert starter.findTopLevelBuildConfDir(str(dir3)) == str(dir3)
    assert starter.findTopLevelBuildConfDir(str(dir2)) is None

    buildconf = joinpath(str(dir1), 'buildconf.yml')
    with open(buildconf, 'w+') as file:
        file.write("buildconf")
    assert starter.findTopLevelBuildConfDir(str(dir4)) == str(dir1)
    assert starter.findTopLevelBuildConfDir(str(dir3)) == str(dir1)
    assert starter.findTopLevelBuildConfDir(str(dir2)) == str(dir1)
    assert starter.findTopLevelBuildConfDir(str(dir1)) == str(dir1)
