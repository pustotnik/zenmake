# coding=utf-8
#

# pylint: disable = wildcard-import, unused-wildcard-import
# pylint: disable = missing-docstring, invalid-name
# pylint: disable = too-many-statements, protected-access

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from zm.pathutils import *

joinpath = os.path.join

def testUnfoldPath():
    # it should be always absolute path
    cwd = os.getcwd()

    abspath = joinpath(cwd, 'something')
    relpath = joinpath('a', 'b', 'c')

    assert unfoldPath(None, cwd) is None
    assert unfoldPath(abspath, cwd) == abspath

    path = unfoldPath(relpath, cwd)
    assert joinpath(cwd, relpath) == path
    assert os.path.isabs(unfoldPath(relpath, abspath))

def testGetNativePath(monkeypatch):

    monkeypatch.setattr(os, 'sep', '/')
    path = 'my/path/to/something'
    assert getNativePath(path) == path

    monkeypatch.setattr(os, 'sep', '\\')
    path = 'my/path/to/something'
    assert getNativePath(path) == path.replace('/', '\\')
