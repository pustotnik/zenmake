# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 This module contains some code to work with python packages/modules,
 especially when they are in zip archives. It has a simple form and only
 needed routines for current project.

 Of course there is pkg_resources from setuptools but setuptools is not part
 of python and using pkg_resources can lead to performance problems:
 https://importlib-resources.readthedocs.io/en/latest/using.html#example:
 > The problem with the pkg_resources approach is that, depending on the
 > structure of your package, pkg_resources can be very inefficient even to
 > just import. pkg_resources is a sort of grab-bag of APIs and functionalities,
 > and to support all of this, it sometimes has to do a ton of work at import
 > time, e.g. to scan every package on your sys.path. This can have a serious
 > negative impact on things like command line startup time for Python
 > implement commands.

 Also in python >= 3.7 threre is importlib.resources which can be used but it's
 only in python >= 3.7.

 Project 'importlib_resources' (https://pypi.org/project/importlib_resources/)
 can be used but again it's not part of python and it is an additional
 dependency when it can be made without it. Also importlib_resources requires
 pathlib2 for python2 and imports module that is not desirable behaivor.

 WARN: this module doesn't support handling outside zip modules. Current
 implementation is not universal solution but it has optimal performance.
"""

import sys
import io
import os
from os.path import isfile, isdir, exists
from zipfile import ZipFile, is_zipfile as iszip

from zm.error import ZenMakeLogicError

class ZipPkg(object):
    """
    Presents routines to work with a zip package if exists.
    """

    def __init__(self, name):
        # It should be zipimporter if current module is loaded from inside
        # of a zip file.
        self._loader = getattr(sys.modules[name], '__loader__', None)
        self._path = None
        if self._loader:
            self._path = getattr(self._loader, 'archive', None)
        # iszip is used to ensure it's really a zip file
        self._zipexists = self._path is not None and iszip(self._path)
        self._paths = None

    def _loadPaths(self):
        with ZipFile(self._path) as archive:
            znames = archive.namelist()

        self._paths = {}
        sep = os.path.sep
        for name in znames:
            # to have a native platform path
            name = name.replace("/", sep)
            node = self._paths
            parts = name.split(sep)
            for part in parts[:-1]:
                if part not in node:
                    node[part] = {}
                node = node[part]
            part = parts[-1]
            # if part is empty string then it's a directory and it's already dict
            if part:
                # it's a file
                node[part] = 'f'

    def _prepareCall(self):
        if not self._zipexists:
            raise ZenMakeLogicError("We aren't inside of a zip file")

        if self._paths is None:
            self._loadPaths()

    def _find(self, path):
        node = self._paths
        if not path:
            return node
        for part in path.split(os.path.sep):
            node = node.get(part, None)
            if node is None:
                return None
        return node

    def get(self, path):
        """ Return a tuple (dirnames, filenames) for selected path """

        self._prepareCall()
        node = self._find(path)
        if node is None:
            return ([],[])

        # make generators
        dirs = (k for k in node if node[k] != 'f')
        files = (k for k in node if node[k] == 'f')
        return (dirs, files)

    def _pathState(self, path):
        self._prepareCall()
        node = self._find(path)
        if node is not None:
            return 'file' if node == 'f' else 'dir'
        return None

    def exists(self, path):
        """ Return True if path exists """
        state = self._pathState(path)
        return state is not None

    def isfile(self, path):
        """ Return True if path exists and it's a file """
        state = self._pathState(path)
        return False if state is None else state == 'file'

    def isdir(self, path):
        """ Return True if path exists and it's a dir """
        state = self._pathState(path)
        return False if state is None else state == 'dir'

    def open(self, path):
        """ Open a file from zip file in binary mode """
        if not self._zipexists:
            raise ZenMakeLogicError("We aren't inside of a zip file")
        data = self._loader.get_data(path)
        return io.BytesIO(data)

    @property
    def zippath(self):
        """ Return path to the zip archive """
        return self._path

    @property
    def zipexists(self):
        """ Return True if zip archive exists """
        return self._zipexists

_localZipPkg = ZipPkg(__name__)

class PkgPath(object):
    """
    Class to work with any python package path/files in a universal way. So path
    can have a zip package file or not.
    """

    def __init__(self, path, zipPkg = None):
        """
        path   - path to process
        zipPkg - object of class ZipPkg, mostly for testing
        """
        self._path = os.path.abspath(path)
        self._zipPkg = _localZipPkg if zipPkg is None else zipPkg
        self._inZip = self._zipPkg.zipexists and \
            self._path.startswith(self._zipPkg.zippath)
        if self._inZip:
            self._zipPath = self._path[len(self._zipPkg.zippath) + 1:]

    def __str__(self):
        return self._path

    @property
    def path(self):
        """ Return string with absolute path """
        return self._path

    def dirs(self):
        """
        Return iterable list of directories as a generator.
        Return empty list if path doesn't exists.
        """

        if self._inZip:
            names, _ = self._zipPkg.get(self._zipPath)
        else:
            _, names, _ = next(os.walk(self._path), (None, [], None))
        return names

    def files(self):
        """
        Return iterable list of files as a generator.
        Return empty list if path doesn't exists.
        """

        if self._inZip:
            _, names = self._zipPkg.get(self._zipPath)
        else:
            _, _, names = next(os.walk(self._path), (None, None, []))
        return names

    def exists(self):
        """ Return True if current path exists """
        if self._inZip:
            return self._zipPkg.exists(self._zipPath)
        return exists(self._path)

    def isdir(self):
        """ Return True if current path exists and it's a directory """
        if self._inZip:
            return self._zipPkg.isdir(self._zipPath)
        return isdir(self._path)

    def isfile(self):
        """ Return True if current path exists and it's a file """
        if self._inZip:
            return self._zipPkg.isfile(self._zipPath)
        return isfile(self._path)

    def open(self):
        """ Open current path as a file in binary mode """
        if self._inZip:
            return self._zipPkg.open(self._zipPath)
        return io.open(self._path, 'rb')

    def openText(self, encoding = 'utf-8'):
        """ Open current path as a file in text mode """
        return io.TextIOWrapper(self.open(), encoding = encoding)

    def read(self):
        """ Read current path as a file in binary mode """
        with self.open() as file:
            return file.read()

    def readText(self, encoding = 'utf-8'):
        """ Read current path as a file in text mode """
        with self.openText(encoding = encoding) as file:
            return file.read()
