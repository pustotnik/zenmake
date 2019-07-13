# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import shutil
import unittest
import tests.common as cmn
import zm.utils

joinpath = os.path.join

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

    def testMkSymlink(self):
        destdir = joinpath(cmn.sharedtmpdir, 'test.util.mksymlink')
        if os.path.exists(destdir):
            shutil.rmtree(destdir)
        os.makedirs(destdir)
        testfile = joinpath(destdir, 'testfile')
        with open(testfile, 'w+') as file:
            file.write("trash")

        symlink = joinpath(destdir, 'symlink')
        zm.utils.mksymlink(testfile, symlink)
        self.assertTrue(os.path.islink(symlink))

        with self.assertRaises(OSError):
            zm.utils.mksymlink(testfile, symlink, force = False)

        zm.utils.mksymlink(testfile, symlink, force = True)
        self.assertTrue(os.path.islink(symlink))
