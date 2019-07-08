#!/usr/bin/env python
# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys 
import os
import unittest
from copy import deepcopy
from contextlib import contextmanager
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import starter
import zm.utils
import zm.buildconfutil
import zm.cli
import zm.assist

joinpath = os.path.join

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_PROJECTS_DIR = joinpath(TESTS_DIR, 'projects')

@contextmanager
def capturedOutput():
    newout, newerr = StringIO(), StringIO()
    oldout, olderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = newout, newerr
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = oldout, olderr

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
            with capturedOutput() as (out, err):
                self.parser.parse(args)
        return cm.exception.code, out.getvalue().strip()

    def _testMainHelpMsg(self, args):
        ecode, out = self._parseHelpArgs(args)
        
        self.assertEqual(ecode, 0)
        self.assertTrue('ZenMake' in out)
        self.assertTrue('based on the Waf build system' in out)
        self.assertIsNotNone(self.parser.command)
        self.assertEqual(self.parser.command.name, 'help')
        self.assertDictEqual(self.parser.command.args, {'topic': 'overview'})
        self.assertListEqual(self.parser.wafCmdLine, [])

    def _assertAllsForCmd(self, cmdname, checks, baseExpectedArgs):
        for check in checks:
            expectedArgs = deepcopy(baseExpectedArgs)
            expectedArgs.update(check['expectedArgsUpdate'])
            cmd = self.parser.parse(check['args'])
            self.assertIsNotNone(cmd)
            self.assertIsNotNone(self.parser.command)
            self.assertEqual(self.parser.command, cmd)
            self.assertEqual(cmd.name, cmdname)
            self.assertDictEqual(cmd.args, expectedArgs)
            for i in xrange(len(check['wafArgs'])):
                wafArg = check['wafArgs'][i]
                self.assertIn(wafArg, self.parser.wafCmdLine[i])

    def testEmpty(self):        
        self._testMainHelpMsg([])

    def testHelp(self):
        self._testMainHelpMsg(['help'])

    def testHelpForCmds(self):
        for cmd in zm.cli._commands:
            args = ['help', cmd.name]
            ecode, out = self._parseHelpArgs(args)
            self.assertEqual(ecode, 0)
            if cmd.name == 'help':
                self.assertTrue('show help' in out)
            else:
                self.assertTrue(cmd.description.capitalize() in out)

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

class TestUtils(unittest.TestCase):
    
    def setUp(self):
        self.longMessage = True

    def tearDown(self):
        pass

    def testUnfoldPath(self):
        # it should be always absolute path
        cwd = os.getcwd()
        
        abspath = joinpath(cwd, 'something')
        relpath = joinpath('a', 'b', 'c')

        self.assertIsNone(zm.utils.unfoldPath(cwd, None))
        self.assertEqual(zm.utils.unfoldPath(cwd, abspath), abspath)
        
        path = zm.utils.unfoldPath(cwd, relpath)
        self.assertEqual(joinpath(cwd, relpath), path)
        self.assertTrue(os.path.isabs(zm.utils.unfoldPath(abspath, relpath)))

        os.environ['ABC'] = 'qwerty'
        
        self.assertEqual(zm.utils.unfoldPath(cwd, joinpath('$ABC', relpath)),
                        joinpath(cwd, 'qwerty', relpath))
