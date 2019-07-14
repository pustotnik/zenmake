# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import shutil
import pytest
import tests.common as cmn
import zm.utils

joinpath = os.path.join

class TestUtils(object):

    def testUnfoldPath(self):
        # it should be always absolute path
        cwd = os.getcwd()

        abspath = joinpath(cwd, 'something')
        relpath = joinpath('a', 'b', 'c')

        assert zm.utils.unfoldPath(cwd, None) is None
        assert zm.utils.unfoldPath(cwd, abspath) == abspath

        path = zm.utils.unfoldPath(cwd, relpath)
        assert joinpath(cwd, relpath) == path
        assert os.path.isabs(zm.utils.unfoldPath(abspath, relpath))

        os.environ['ABC'] = 'qwerty'

        assert joinpath(cwd, 'qwerty', relpath) == \
                        zm.utils.unfoldPath(cwd, joinpath('$ABC', relpath))

    def testMkSymlink(self):
        destdir = joinpath(cmn.SHARED_TMP_DIR, 'test.util.mksymlink')
        if os.path.exists(destdir):
            shutil.rmtree(destdir)
        os.makedirs(destdir)
        testfile = joinpath(destdir, 'testfile')
        with open(testfile, 'w+') as file:
            file.write("trash")

        symlink = joinpath(destdir, 'symlink')
        zm.utils.mksymlink(testfile, symlink)
        assert os.path.islink(symlink)

        with pytest.raises(OSError):
            zm.utils.mksymlink(testfile, symlink, force = False)

        zm.utils.mksymlink(testfile, symlink, force = True)
        assert os.path.islink(symlink)
