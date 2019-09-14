# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from zipimport import zipimporter
import pytest
import tests.common as cmn
from zm import pypkg, pyutils, error

joinpath = os.path.join

MODULE_ZIP_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ZIP_PATH = joinpath(MODULE_ZIP_DIR, 'module.zip')

@pytest.fixture
def zipPkg(monkeypatch):
    zipImporter = zipimporter(MODULE_ZIP_PATH)
    setattr(pypkg, '__loader__', None)
    monkeypatch.setattr(pypkg, '__loader__', zipImporter)
    return pypkg.ZipPkg(pypkg.__name__)

def testZipPkgErrors():
    zipPkg = pypkg.ZipPkg(pypkg.__name__)
    with pytest.raises(error.ZenMakeError):
        zipPkg.get('')
    with pytest.raises(error.ZenMakeError):
        zipPkg.open('')

def testPath():
    path = os.path.join('aaa', 'bbb')
    pkgPath = pypkg.PkgPath(path)
    assert pkgPath.path == os.path.abspath(path)
    assert str(pkgPath) == pkgPath.path

def testDirs(tmpdir, zipPkg):

    # 'dirs' without a zip
    tmpDirPath = str(tmpdir.realpath())
    tmpdir.mkdir("aaa")
    tmpdir.mkdir('bbb')
    pkgPath = pypkg.PkgPath(tmpDirPath)
    assert sorted(['aaa', 'bbb']) == sorted(pkgPath.dirs())
    pkgPath = pypkg.PkgPath(joinpath(tmpDirPath, 'notexisting'))
    assert list(pkgPath.dirs()) == []

    # 'exists', 'isfile', 'isdir' without a zip
    assert pypkg.PkgPath(joinpath(tmpDirPath, 'aaa')).exists()
    assert pypkg.PkgPath(joinpath(tmpDirPath, 'aaa')).isdir()
    assert not pypkg.PkgPath(joinpath(tmpDirPath, 'aaa')).isfile()
    assert not pypkg.PkgPath(joinpath(tmpDirPath, 'notexisting')).exists()
    assert not pypkg.PkgPath(joinpath(tmpDirPath, 'notexisting')).isdir()
    assert not pypkg.PkgPath(joinpath(tmpDirPath, 'notexisting')).isfile()

    # 'dirs' with a zip
    pkgPath = pypkg.PkgPath(MODULE_ZIP_PATH, zipPkg)
    assert sorted(pkgPath.dirs()) == sorted(['pkg1', 'pkg2'])
    pkgPath = pypkg.PkgPath(joinpath(MODULE_ZIP_PATH, 'pkg2'), zipPkg)
    assert list(pkgPath.dirs()) == ['pkg3']
    pkgPath = pypkg.PkgPath(joinpath(MODULE_ZIP_PATH, 'notexisting'), zipPkg)
    assert list(pkgPath.dirs()) == []

    # 'exists', 'isfile', 'isdir' with a zip
    path = joinpath(MODULE_ZIP_PATH, 'pkg1')
    assert pypkg.PkgPath(path, zipPkg).exists()
    assert pypkg.PkgPath(path, zipPkg).isdir()
    assert not pypkg.PkgPath(path, zipPkg).isfile()
    path = joinpath(MODULE_ZIP_PATH, 'notexisting')
    assert not pypkg.PkgPath(path, zipPkg).exists()
    assert not pypkg.PkgPath(path, zipPkg).isdir()
    assert not pypkg.PkgPath(path, zipPkg).isfile()

def testFiles(tmpdir, zipPkg):

    # 'files' without a zip
    tmpDirPath = str(tmpdir.realpath())
    aaaDir = tmpdir.mkdir("aaa")
    aaaDir.join("a1").write('111')
    aaaDir.join("a2").write('111')
    pkgPath = pypkg.PkgPath(str(aaaDir))
    assert sorted(['a1', 'a2']) == sorted(pkgPath.files())
    pkgPath = pypkg.PkgPath(joinpath(tmpDirPath, 'notexisting'))
    assert list(pkgPath.files()) == []

    # 'exists', 'isfile', 'isdir' without a zip
    assert pypkg.PkgPath(joinpath(str(aaaDir), 'a1')).exists()
    assert pypkg.PkgPath(joinpath(str(aaaDir), 'a1')).isfile()
    assert not pypkg.PkgPath(joinpath(str(aaaDir), 'a1')).isdir()
    assert not pypkg.PkgPath(joinpath(str(aaaDir), 'notexisting')).exists()
    assert not pypkg.PkgPath(joinpath(str(aaaDir), 'notexisting')).isfile()
    assert not pypkg.PkgPath(joinpath(str(aaaDir), 'notexisting')).isdir()

    # 'files' with a zip
    pkgPath = pypkg.PkgPath(MODULE_ZIP_PATH, zipPkg)
    assert list(pkgPath.files()) == ['module.py']
    pkgPath = pypkg.PkgPath(joinpath(MODULE_ZIP_PATH, 'pkg1'), zipPkg)
    assert sorted(pkgPath.files()) == sorted(['module1.py', 'module2.py'])
    pkgPath = pypkg.PkgPath(joinpath(MODULE_ZIP_PATH, 'notexisting'), zipPkg)
    assert list(pkgPath.files()) == []

    # 'exists', 'isfile', 'isdir' with a zip
    path = joinpath(MODULE_ZIP_PATH, 'pkg1', 'module1.py')
    assert pypkg.PkgPath(path, zipPkg).exists()
    assert pypkg.PkgPath(path, zipPkg).isfile()
    assert not pypkg.PkgPath(path, zipPkg).isdir()
    path = joinpath(MODULE_ZIP_PATH, 'pkg1', 'notexisting')
    assert not pypkg.PkgPath(path, zipPkg).exists()
    assert not pypkg.PkgPath(path, zipPkg).isdir()
    assert not pypkg.PkgPath(path, zipPkg).isfile()

def testOpenRead(tmpdir, zipPkg):

    # without a zip
    tmpDirPath = str(tmpdir.realpath())
    aaaDir = tmpdir.mkdir("aaa")
    aaaDir.join("a1").write('111')

    pkgPath = pypkg.PkgPath(joinpath(str(aaaDir), 'a1'))
    data = pkgPath.read()
    assert isinstance(data, pyutils.binarytype)
    assert data == b'111'

    data = pkgPath.readText()
    assert isinstance(data, pyutils.texttype)
    assert data == '111'

    # with a zip
    path = joinpath(MODULE_ZIP_PATH, 'pkg2', 'pkg3', 'module2.py')
    pkgPath = pypkg.PkgPath(path, zipPkg)
    data = pkgPath.read()
    assert isinstance(data, pyutils.binarytype)
    assert b'something' in data

    data = pkgPath.readText()
    assert isinstance(data, pyutils.texttype)
    assert 'something' in data