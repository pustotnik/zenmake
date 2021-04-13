# coding=utf-8
#

# pylint: disable = missing-docstring, invalid-name
# pylint: disable = too-many-statements, protected-access

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import pytest
from waflib.ConfigSet import ConfigSet
from zm import utils, error
from zm.constants import PLATFORM
from zm.pypkg import PkgPath

joinpath = os.path.join

def testMkSymlink(tmpdir, monkeypatch):

    destdir = str(tmpdir.realpath())
    testfile = joinpath(destdir, 'testfile')
    with open(testfile, 'w+') as file:
        file.write("trash")

    if PLATFORM == 'windows':
        _mksymlink = getattr(os, "symlink", None)
        if callable(_mksymlink):
            try:
                _mksymlink(testfile, joinpath(destdir, 'a'))
            except OSError:
                # On windows we have no implemention or rights to make symlink
                return

    symlink = joinpath(destdir, 'symlink')
    utils.mksymlink(testfile, symlink)
    assert os.path.islink(symlink)

    with pytest.raises(OSError):
        utils.mksymlink(testfile, symlink, force = False)

    utils.mksymlink(testfile, symlink, force = True)
    assert os.path.islink(symlink)

    monkeypatch.setattr(os, "symlink", None)
    with pytest.raises(NotImplementedError):
        utils.mksymlink(testfile, symlink)

def testToListSimple():

    assert utils.toListSimple('') == list()
    assert utils.toListSimple('abc') == ['abc']
    assert utils.toListSimple('a1 a2   b1 b2') == ['a1', 'a2', 'b1', 'b2']
    assert utils.toListSimple(['a1', 'a2', 'b1']) == ['a1', 'a2', 'b1']

def testToList():

    assert utils.toList('') == list()
    assert utils.toList('abc') == ['abc']
    assert utils.toList('a1 a2   b1 b2') == ['a1', 'a2', 'b1', 'b2']
    assert utils.toList(['a1', 'a2', 'b1']) == ['a1', 'a2', 'b1']

    assert utils.toList('a1 "a2"   b1 b2') == ['a1', 'a2', 'b1', 'b2']

    src = """   aa bb 'cc 111 ccc ' " aaa 'bb'"  dd   val1=" A1 " val2='A2'"""
    assert utils.toList(src) == \
        ['aa', 'bb', 'cc 111 ccc ', " aaa 'bb'", 'dd', 'val1=" A1 "', "val2='A2'"]

def testNormalizeForFileName(monkeypatch):
    assert utils.normalizeForFileName('abc') == 'abc'
    assert utils.normalizeForFileName(' abc ') == 'abc'
    assert utils.normalizeForFileName('a b c') == 'a_b_c'
    assert utils.normalizeForFileName('a b c', spaceAsDash = True) == 'a-b-c'
    assert utils.normalizeForFileName(' aBc<>:?*.e ') == 'aBc.e'
    monkeypatch.setattr(utils, 'PLATFORM', 'windows')
    assert utils.normalizeForFileName('aux') == '_aux'

def testLoadPyModule(mocker, monkeypatch):

    cwd = os.path.abspath(os.path.dirname(__file__))
    oldSysPath = sys.path

    def checkModule(module, withImport):
        assert module
        assert type(module) == type(sys)
        assert hasattr(module, '__name__')
        assert hasattr(module, '__file__')
        moduleFile = os.path.abspath(module.__file__).lower()
        assert hasattr(module, '__package__')
        name = module.__name__
        if not withImport:
            basename = moduleFile.split(os.path.sep)[-1]
            isPkg = basename.startswith('__init__.py')
            if isPkg:
                assert module.__package__ == name
            else:
                assert module.__package__ == '.'.join(name.split('.')[:-1])
        assert hasattr(module, 'something')
        assert module.something == 'qaz'
        if withImport:
            assert name in sys.modules
            assert sys.modules[name] == module

    with pytest.raises(ImportError):
        utils.loadPyModule('notexisting', dirpath = None, withImport = True)
    with pytest.raises(ImportError):
        utils.loadPyModule('notexisting', dirpath = None, withImport = False)

    name = 'tests.fakemodule'
    dirpath = os.path.realpath(joinpath(cwd, os.path.pardir))

    # withImport = False
    module = utils.loadPyModule(name, dirpath = 'notexisting', withImport = False)
    checkModule(module, False)
    module = utils.loadPyModule(name, dirpath = None, withImport = False)
    checkModule(module, False)
    module = utils.loadPyModule(name, dirpath = dirpath, withImport = False)
    checkModule(module, False)

    # withImport = True
    module = utils.loadPyModule(name, dirpath = 'notexisting', withImport = True)
    checkModule(module, True)
    module = utils.loadPyModule(name, dirpath = None, withImport = True)
    checkModule(module, True)
    module = utils.loadPyModule(name, dirpath = dirpath, withImport = True)
    checkModule(module, True)

    name = 'fakemodule'
    dirpath = os.path.realpath(cwd)

    # withImport = False
    with pytest.raises(ImportError):
        utils.loadPyModule(name, dirpath = None, withImport = False)
    with pytest.raises(ImportError):
        utils.loadPyModule(name, dirpath = 'notexisting', withImport = False)
    module = utils.loadPyModule(name, dirpath = dirpath, withImport = False)
    checkModule(module, False)

    # withImport = True
    with pytest.raises(ImportError):
        utils.loadPyModule(name, dirpath = None, withImport = True)
    with pytest.raises(ImportError):
        utils.loadPyModule(name, dirpath = 'notexisting', withImport = True)
    module = utils.loadPyModule(name, dirpath = dirpath, withImport = True)
    checkModule(module, True)

    name = 'tests'
    dirpath = os.path.realpath(joinpath(cwd, os.path.pardir))

    # withImport = False
    module = utils.loadPyModule(name, dirpath = 'notexisting', withImport = False)
    checkModule(module, False)
    module = utils.loadPyModule(name, dirpath = None, withImport = False)
    checkModule(module, False)
    module = utils.loadPyModule(name, dirpath = dirpath, withImport = False)
    checkModule(module, False)

    # errors
    monkeypatch.setattr(PkgPath, "read",
                        mocker.MagicMock(side_effect = EnvironmentError))
    with pytest.raises(error.ZenMakeError):
        utils.loadPyModule(name, dirpath = None, withImport = False)


    assert oldSysPath == sys.path

def testCopyEnv():
    rootenv = ConfigSet()
    rootenv.test1 = 'test1'
    childenv = rootenv.derive()
    childenv.test2 = 'test2'
    newenv = utils.copyEnv(childenv)
    assert childenv.test1 == 'test1'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'test1'
    assert newenv.test2 == 'test2'
    rootenv.test1 = 'abc'
    assert childenv.test1 == 'abc'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'abc'
    assert newenv.test2 == 'test2'
    childenv.test2 = 'dfg'
    assert childenv.test2 == 'dfg'
    assert newenv.test2 == 'test2'

def testDeepCopyEnv():
    rootenv = ConfigSet()
    rootenv.test1 = 'test1'
    childenv = rootenv.derive()
    childenv.test2 = 'test2'
    newenv = utils.deepcopyEnv(childenv)
    assert childenv.test1 == 'test1'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'test1'
    assert newenv.test2 == 'test2'
    rootenv.test1 = 'abc'
    assert childenv.test1 == 'abc'
    assert childenv.test2 == 'test2'
    assert newenv.test1 == 'test1'
    assert newenv.test2 == 'test2'
    childenv.test2 = 'dfg'
    assert childenv.test2 == 'dfg'
    assert newenv.test2 == 'test2'
