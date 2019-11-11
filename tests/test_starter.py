# coding=utf-8
#

# pylint: skip-file

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
    bconfHandler = AutoDict(
        defaultBuildType = '',
        options = {},
    )

    with pytest.raises(SystemExit):
        starter.handleCLI(args, noBuildConf, bconfHandler)
    # clean output
    capsys.readouterr()

    with pytest.raises(SystemExit):
        starter.handleCLI(args, noBuildConf, None)
    # clean output
    capsys.readouterr()

    #############
    args = [APPNAME, 'build']
    bconfHandler.options = {}
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, bconfHandler)
    assert cmd == cli.selected
    assert cmd.name == 'build'
    assert wafCmdLine[0] == 'build'
    assert cmd.args.verbose == 0
    assert cmd.args.jobs is None
    assert not cmd.args.progress

    bconfHandler.options = {
        'verbose': 1,
        'jobs' : { 'build' : 4 },
        'progress' : {'any': False, 'build': True },
    }
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, bconfHandler)
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
    cmd, wafCmdLine = starter.handleCLI(args, noBuildConf, bconfHandler)
    assert cmd == cli.selected
    assert cmd.name == 'test'
    assert wafCmdLine[0] == 'build'
    assert cmd.args.verbose == 1
    assert cmd.args.jobs is None
    assert not cmd.args.progress
