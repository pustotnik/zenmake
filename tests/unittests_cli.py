# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import unittest
from copy import deepcopy
import tests.common as cmn
import zm.buildconfutil
import zm.cli

class TestCli(unittest.TestCase):

    def setUp(self):
        self.longMessage = True
        self.buildconf = zm.buildconfutil.loadConf()
        self.parser = zm.cli.CmdLineParser('test')

    def tearDown(self):
        pass

    def _parseHelpArgs(self, args):
        # CLI prints help and does exit
        with self.assertRaises(SystemExit) as cm:
            with cmn.capturedOutput() as (out, err):
                self.parser.parse(args)
        return cm.exception.code, out.getvalue().strip(), err.getvalue().strip()

    def _testMainHelpMsg(self, args):
        ecode, out, err = self._parseHelpArgs(args)

        self.assertFalse(err)
        self.assertEqual(ecode, 0)
        self.assertIn('ZenMake', out)
        self.assertIn('based on the Waf build system', out)
        self.assertIsNotNone(self.parser.command)
        self.assertEqual(self.parser.command.name, 'help')
        self.assertDictEqual(self.parser.command.args, {'topic': 'overview'})
        self.assertListEqual(self.parser.wafCmdLine, [])

    def _assertAllsForCmd(self, cmdname, checks, baseExpectedArgs):

        for check in checks:
            expectedArgs = deepcopy(baseExpectedArgs)
            expectedArgs.update(check['expectedArgsUpdate'])

            def assertAll(cmd, parsercmd, wafcmdline):
                self.assertIsNotNone(cmd)
                self.assertIsNotNone(parsercmd)
                self.assertEqual(parsercmd, cmd)
                self.assertEqual(cmd.name, cmdname)
                self.assertDictEqual(cmd.args, expectedArgs)
                for i in range(len(check['wafArgs'])):
                    wafArg = check['wafArgs'][i]
                    self.assertIn(wafArg, wafcmdline[i])

            # parser with explicit args
            cmd = self.parser.parse(check['args'])
            assertAll(cmd, self.parser.command, self.parser.wafCmdLine)

            # parser with args from sys.argv
            oldargv = sys.argv
            sys.argv = ['zenmake'] + check['args']
            cmd = self.parser.parse()
            sys.argv = oldargv
            assertAll(cmd, self.parser.command, self.parser.wafCmdLine)

            # zm.cli.parseAll
            wafCmdLine = zm.cli.parseAll(['zenmake'] + check['args'])
            assertAll(zm.cli.selected, zm.cli.selected, wafCmdLine)

    def testEmpty(self):
        self._testMainHelpMsg([])

    def testHelp(self):
        self._testMainHelpMsg(['help'])

    def testHelpWrongTopic(self):
        args = ['help', 'qwerty']
        ecode, out, err = self._parseHelpArgs(args)
        self.assertFalse(out)
        self.assertIn('Unknown command/topic', err)
        self.assertNotEqual(ecode, 0)

    def testHelpForCmds(self):
        for cmd in zm.cli._commands:
            args = ['help', cmd.name]
            ecode, out, err = self._parseHelpArgs(args)
            self.assertEqual(ecode, 0)
            self.assertFalse(err)
            if cmd.name == 'help':
                self.assertIn('show help', out)
            else:
                self.assertIn(cmd.description.capitalize(), out)

    def testCmdBuild(self):

        baseExpectedArgs = {
            'buildtype' : self.buildconf.buildtypes['default'],
            'jobs' : None,
            'configure': False,
            'color': 'auto',
            'clean': False,
            'progress': False,
            'distclean': False,
            'buildtasks': [],
            'verbose': 0,
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
                expectedArgsUpdate = {'buildtasks': ['sometask']},
                wafArgs = [CMDNAME],
            ),
            dict(
                args = [CMDNAME, 'sometask', 'anothertask'],
                expectedArgsUpdate = {'buildtasks': ['sometask', 'anothertask']},
                wafArgs = [CMDNAME],
            ),
        ]

        self._assertAllsForCmd(CMDNAME, checks, baseExpectedArgs)

    def testCmdConfigure(self):

        baseExpectedArgs = {
            'buildtype' : self.buildconf.buildtypes['default'],
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
            'buildtype' : self.buildconf.buildtypes['default'],
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
