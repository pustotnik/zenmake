# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
from copy import deepcopy
import pytest
import tests.common as cmn
from zm import cli

class TestSuite(object):

    @pytest.fixture(autouse = True)
    def setup(self):
        self.defaults = { '*' : { 'buildtype': 'somedebug' } }
        self.parser = cli.CmdLineParser('test', self.defaults)

    def _parseHelpArgs(self, args, capsys):
        # CLI prints help and does exit
        with pytest.raises(SystemExit) as cm:
            self.parser.parse(args)
        captured = capsys.readouterr()
        return cm.value.code, captured.out, captured.err

    def _testMainHelpMsg(self, args, capsys):
        ecode, out, err = self._parseHelpArgs(args, capsys)

        assert not err
        assert ecode == 0
        assert 'ZenMake' in out
        assert 'based on the Waf build system' in out
        assert self.parser.command is not None
        assert self.parser.command.name == 'help'
        assert self.parser.command.args == {'topic': 'overview'}
        assert self.parser.wafCmdLine == []

    def _assertAllsForCmd(self, cmdname, checks, baseExpectedArgs):

        for check in checks:
            expectedArgs = deepcopy(baseExpectedArgs)
            expectedArgs.update(check['expectedArgsUpdate'])

            def assertAll(cmd, parsercmd, wafcmdline):
                assert cmd is not None
                assert parsercmd is not None
                assert parsercmd == cmd
                assert cmd.name == cmdname
                assert cmd.args == expectedArgs
                for i in range(len(check['wafArgs'])):
                    wafArg = check['wafArgs'][i]
                    assert wafArg in wafcmdline[i]

            # parser with explicit args
            cmd = self.parser.parse(check['args'])
            assertAll(cmd, self.parser.command, self.parser.wafCmdLine)

            # parser with args from sys.argv
            oldargv = sys.argv
            sys.argv = ['zenmake'] + check['args']
            cmd = self.parser.parse()
            sys.argv = oldargv
            assertAll(cmd, self.parser.command, self.parser.wafCmdLine)

    def testEmpty(self, capsys):
        self._testMainHelpMsg([], capsys)

    def testHelp(self, capsys):
        self._testMainHelpMsg(['help'], capsys)

    def testHelpWrongTopic(self, capsys):
        args = ['help', 'qwerty']
        ecode, out, err = self._parseHelpArgs(args, capsys)
        assert not out
        assert 'Unknown command/topic' in err
        assert ecode != 0

    def testHelpForCmds(self, capsys):
        for cmd in cli._commands:
            args = ['help', cmd.name]
            ecode, out, err = self._parseHelpArgs(args, capsys)
            assert ecode == 0
            assert not err
            if cmd.name == 'help':
                assert 'show help' in out
            else:
                assert cmd.description.capitalize() in out

    def testCmdBuild(self):

        baseExpectedArgs = {
            'buildtype' : self.defaults['*']['buildtype'],
            'jobs' : None,
            'configure': False,
            'color': 'auto',
            'clean': False,
            'progress': False,
            'distclean': False,
            'tasks': [],
            'verbose': 0,
            'buildTests': False,
            'runTests': 'none',
        }

        CMDNAME = 'build'
        checks = [
            dict(
                args = [CMDNAME],
                expectedArgsUpdate = {},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '-b', 'release'],
                expectedArgsUpdate = {'buildtype': 'release'},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--jobs', '22'],
                expectedArgsUpdate = {'jobs': 22},
                wafArgs = [CMDNAME, '--jobs=22'],
            ),
            dict(
                args = [CMDNAME, '--verbose'],
                expectedArgsUpdate = {'verbose': 1},
                wafArgs = [CMDNAME, '-v'],
            ),
            dict(
                args = [CMDNAME, '-vvv'],
                expectedArgsUpdate = {'verbose': 3},
                wafArgs = [CMDNAME, '-vvv'],
            ),
            dict(
                args = [CMDNAME, '--configure'],
                expectedArgsUpdate = {'configure': True},
                wafArgs = ['configure', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--clean'],
                expectedArgsUpdate = {'clean': True},
                wafArgs = ['clean', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--distclean'],
                expectedArgsUpdate = {'distclean': True},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--build-tests', 'yes'],
                expectedArgsUpdate = {'buildTests': True},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--run-tests', 'all'],
                expectedArgsUpdate = {'runTests': 'all'},
                wafArgs = [CMDNAME, 'test'],
            ),
            dict(
                args = [CMDNAME, '--run-tests', 'on-changes'],
                expectedArgsUpdate = {'runTests': 'on-changes'},
                wafArgs = [CMDNAME, 'test'],
            ),
            dict(
                args = [CMDNAME, '--progress'],
                expectedArgsUpdate = {'progress': True},
                wafArgs = [CMDNAME, '--progress'],
            ),
            dict(
                args = [CMDNAME, '--color', 'no'],
                expectedArgsUpdate = {'color': 'no'},
                wafArgs = [CMDNAME, '--color=no'],
            ),
            dict(
                args = [CMDNAME, 'sometask'],
                expectedArgsUpdate = {'tasks': ['sometask']},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, 'sometask', 'anothertask'],
                expectedArgsUpdate = {'tasks': ['sometask', 'anothertask']},
                wafArgs = [CMDNAME],
            ),
        ]

        self._assertAllsForCmd(CMDNAME, checks, baseExpectedArgs)

    def testCmdTest(self):

        baseExpectedArgs = {
            'buildtype' : self.defaults['*']['buildtype'],
            'jobs' : None,
            'configure': False,
            'color': 'auto',
            'clean': False,
            'progress': False,
            'distclean': False,
            'tasks': [],
            'verbose': 0,
            'buildTests': True,
            'runTests': 'all',
        }

        CMDNAME = 'test'

        checks = [
            dict(
                args = [CMDNAME],
                expectedArgsUpdate = {},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '-b', 'release'],
                expectedArgsUpdate = {'buildtype': 'release'},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--jobs', '22'],
                expectedArgsUpdate = {'jobs': 22},
                wafArgs = ['build', CMDNAME, '--jobs=22'],
            ),
            dict(
                args = [CMDNAME, '--verbose'],
                expectedArgsUpdate = {'verbose': 1},
                wafArgs = ['build', CMDNAME, '-v'],
            ),
            dict(
                args = [CMDNAME, '-vvv'],
                expectedArgsUpdate = {'verbose': 3},
                wafArgs = ['build', CMDNAME, '-vvv'],
            ),
            dict(
                args = [CMDNAME, '--configure'],
                expectedArgsUpdate = {'configure': True},
                wafArgs = ['configure', 'build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--clean'],
                expectedArgsUpdate = {'clean': True},
                wafArgs = ['clean', 'build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--distclean'],
                expectedArgsUpdate = {'distclean': True},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--build-tests', 'no'],
                expectedArgsUpdate = {'buildTests': False},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--run-tests', 'none'],
                expectedArgsUpdate = {'runTests': 'none'},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--run-tests', 'on-changes'],
                expectedArgsUpdate = {'runTests': 'on-changes'},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--progress'],
                expectedArgsUpdate = {'progress': True},
                wafArgs = ['build', CMDNAME, '--progress'],
            ),
            dict(
                args = [CMDNAME, '--color', 'no'],
                expectedArgsUpdate = {'color': 'no'},
                wafArgs = ['build', CMDNAME, '--color=no'],
            ),
            dict(
                args = [CMDNAME, 'sometask'],
                expectedArgsUpdate = {'tasks': ['sometask']},
                wafArgs = ['build', CMDNAME],
            ),
            dict(
                args = [CMDNAME, 'sometask', 'anothertask'],
                expectedArgsUpdate = {'tasks': ['sometask', 'anothertask']},
                wafArgs = ['build', CMDNAME],
            ),
        ]

        self._assertAllsForCmd(CMDNAME, checks, baseExpectedArgs)

    def testCmdConfigure(self):

        baseExpectedArgs = {
            'buildtype' : self.defaults['*']['buildtype'],
            'color': 'auto',
            'distclean': False,
            'verbose': 0,
        }

        CMDNAME = 'configure'
        checks = [
            dict(
                args = [CMDNAME],
                expectedArgsUpdate = {},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '-b', 'release'],
                expectedArgsUpdate = {'buildtype': 'release'},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--distclean'],
                expectedArgsUpdate = {'distclean': True},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--verbose'],
                expectedArgsUpdate = {'verbose': 1},
                wafArgs = [CMDNAME, '-v'],
            ),
            dict(
                args = [CMDNAME, '-vvv'],
                expectedArgsUpdate = {'verbose': 3},
                wafArgs = [CMDNAME, '-vvv'],
            ),
            dict(
                args = [CMDNAME, '--color', 'no'],
                expectedArgsUpdate = {'color': 'no'},
                wafArgs = [CMDNAME, '--color=no'],
            ),
        ]

        self._assertAllsForCmd(CMDNAME, checks, baseExpectedArgs)

    def testCmdClean(self):

        baseExpectedArgs = {
            'buildtype' : self.defaults['*']['buildtype'],
            'color': 'auto',
            'verbose': 0,
        }

        CMDNAME = 'clean'
        checks = [
            dict(
                args = [CMDNAME],
                expectedArgsUpdate = {},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '-b', 'release'],
                expectedArgsUpdate = {'buildtype': 'release'},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--verbose'],
                expectedArgsUpdate = {'verbose': 1},
                wafArgs = [CMDNAME, '-v'],
            ),
            dict(
                args = [CMDNAME, '-vvv'],
                expectedArgsUpdate = {'verbose': 3},
                wafArgs = [CMDNAME, '-vvv'],
            ),
            dict(
                args = [CMDNAME, '--color', 'no'],
                expectedArgsUpdate = {'color': 'no'},
                wafArgs = [CMDNAME, '--color=no'],
            ),
        ]

        self._assertAllsForCmd(CMDNAME, checks, baseExpectedArgs)

    def testCmdDistclean(self):

        baseExpectedArgs = {
            'color': 'auto',
            'verbose': 0,
        }

        CMDNAME = 'distclean'
        checks = [
            dict(
                args = [CMDNAME],
                expectedArgsUpdate = {},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, '--verbose'],
                expectedArgsUpdate = {'verbose': 1},
                wafArgs = [CMDNAME, '-v'],
            ),
            dict(
                args = [CMDNAME, '-vvv'],
                expectedArgsUpdate = {'verbose': 3},
                wafArgs = [CMDNAME, '-vvv'],
            ),
            dict(
                args = [CMDNAME, '--color', 'no'],
                expectedArgsUpdate = {'color': 'no'},
                wafArgs = [CMDNAME, '--color=no'],
            ),
        ]

        self._assertAllsForCmd(CMDNAME, checks, baseExpectedArgs)
