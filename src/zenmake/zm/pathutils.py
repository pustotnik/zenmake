# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from waflib.Node import exclude_regs as DEFAULT_PATH_EXCLUDES
from zm.pyutils import PY2, maptype, stringtype
from zm.utils import toList, toListSimple
from zm.error import ZenMakePathNotFoundError, ZenMakeDirNotFoundError

DEFAULT_PATH_EXCLUDES = toListSimple(DEFAULT_PATH_EXCLUDES)

_joinpath = os.path.join
_abspath = os.path.abspath
_normpath = os.path.normpath
_relpath = os.path.relpath
_isabs = os.path.isabs
_isdir = os.path.isdir
_expandvars = os.path.expandvars
_expanduser = os.path.expanduser

def unfoldPath(cwd, path):
    """
    Unfold path applying os.path.expandvars and os.path.expanduser.
    Join 'path' with 'cwd' in the beginning If 'path' is not absolute path.
    Returns normalized absolute path.
    """

    if not path:
        return path

    path = _expandvars(path)
    path = _expanduser(path)
    if not _isabs(path):
        path = _joinpath(cwd, path)
    path = _abspath(path)
    return path

def getNativePath(path):
    """
    Return native path from POSIX path
    """
    if not path:
        return path
    return path.replace('/', os.sep) if os.sep != '/' else path

class PathsParam(object):
    """
    Class to hold param with path(s)
    """

    __slots__ = ('_value', '_startdir', '_kind', '_cache')

    _CLS_NAME = __module__ + '.PathsParam'

    def __init__(self, value, startdir, rootdir = None, kind = None):
        """
        Param 'startdir' is expected as absolute path. But if 'rootdir' is an
        absolute path then 'startdir' can be relative path and resulting
        'startdir' will be 'rootdir' + 'startdir'.
        """

        if kind is None:
            if isinstance(value, (list, tuple)):
                kind = 'paths'
            else:
                kind = 'path'
                value = (value,)
        else:
            if kind == 'paths':
                value = toList(value)
            elif kind == 'path':
                value = (value,)
            else:
                raise NotImplementedError

        if rootdir is not None:
            startdir = _normpath(_joinpath(rootdir, startdir))

        value = [ getNativePath(x) for x in value ]
        # value can contain absolute and/or relative paths
        value = [ _normpath(_relpath(x, startdir) if _isabs(x) else x) for x in value ]

        self._startdir = startdir

        self._kind = kind
        self._value = value
        self._cache = {
            # while current startdir is unchanged 'value' contains paths
            # relative to the current startdir
            'relpaths' : value,
        }

    @classmethod
    def makeFrom(cls, pathsParam, startdir = None, rootdir = None, kind = None):
        """ Make the new object as a copy of pathsParam """

        # pylint: disable = protected-access

        self = cls.__new__(cls)

        otherKind     = pathsParam._kind
        otherStartdir = pathsParam._startdir
        otherVal      = pathsParam._value
        otherCache    = pathsParam._cache

        if kind is not None and kind != otherKind:
            if kind == 'paths':
                self._kind = kind
            elif kind == 'path':
                self._kind = kind
                otherVal = pathsParam._value[0:1]
            else:
                raise NotImplementedError
        else:
            self._kind = otherKind

        self._value = list(otherVal)
        self._cache = {}

        otherAbsPaths = otherCache.get('abspaths')
        if otherAbsPaths is not None:
            self._cache['abspaths'] = list(otherAbsPaths)

        self._startdir = otherStartdir
        if startdir is not None and startdir != otherStartdir:
            if rootdir is not None:
                startdir = _normpath(_joinpath(rootdir, startdir))
            self.abspaths()
            self._startdir = startdir
        else:
            otherRelPaths = otherCache.get('relpaths')
            if otherRelPaths is not None:
                if id(otherRelPaths) == id(otherVal):
                    # optimization of cache using
                    self._cache['relpaths'] = self._value
                else:
                    self._cache['relpaths'] = list(otherRelPaths)
        return self

    @property
    def startdir(self):
        """ Get current startdir """
        return self._startdir

    @startdir.setter
    def startdir(self, val):
        """
        Set new startdir. It doesn't change absolute path(s).
        It changes relative path(s).
        """

        if val == self._startdir:
            return

        self._cache.pop('relpaths', None)
        # force abspaths before change of startdir
        self.abspaths()
        self._startdir = val

    def _changeBySlice(self, ibeg, iend, value, startdir = None):

        assert self._kind == 'paths'

        # get as absolute paths
        if isinstance(value, PathsParam):
            # startdir is not important in this case
            value = value.abspaths()
        else:
            if startdir is None:
                startdir = self._startdir
            value = [_normpath(_joinpath(startdir, x)) for x in value]

        # update abspaths
        abspaths = self._cache.get('abspaths')
        if abspaths is not None:
            abspaths[ibeg:iend] = value

        # convert to relative paths
        startdir = self._startdir
        value = [ _relpath(x, startdir) for x in value]

        # update value
        self._value[ibeg:iend] = value

        # update relpaths
        relpaths = self._cache.get('relpaths')
        if relpaths is not None and id(relpaths) != id(self._value):
            relpaths[ibeg:iend] = value

    def insert(self, index, paths, startdir = None):
        """ Insert paths. Can be used only if kind == 'paths' """
        self._changeBySlice(index, index, paths, startdir)

    def insertFrom(self, index, pathsParam):
        """
        Insert paths from another PathsParam object.
        Can be used only if kind == 'paths'
        """
        self._changeBySlice(index, index, pathsParam)

    def extend(self, paths, startdir = None):
        """ Extend with paths. Can be used only if kind == 'paths' """
        _len = len(self._value)
        self._changeBySlice(_len, _len, paths, startdir)

    def extendFrom(self, pathsParam):
        """
        Extend with paths from PathsParam object.
        Can be used only if kind == 'paths'
        """

        _len = len(self._value)
        self._changeBySlice(_len, _len, pathsParam)

    def abspaths(self):
        """
        Get absolute paths in sorted order
        """

        abspaths = self._cache.get('abspaths')

        if abspaths is None:
            startdir = self._startdir
            abspaths = [ _normpath(_joinpath(startdir, x)) for x in self._value]
            self._cache['abspaths'] = abspaths

        return abspaths

    def relpaths(self, applyStartDir = None):
        """
        Get relative paths in sorted order
        """

        if applyStartDir is not None:
            self.startdir = applyStartDir

        relpaths = self._cache.get('relpaths')

        if relpaths is None:
            abspaths = self.abspaths()
            startdir = self._startdir
            # self.abspaths are always norm paths
            relpaths = [ _relpath(x, startdir) for x in abspaths]
            # there are no reasons to hold two lists of relative paths
            self._cache['relpaths'] = self._value = relpaths

        return relpaths

    def abspath(self):
        """
        Get absolute path if kind == 'path'.
        This method is for convenience only.
        """

        assert self._kind == 'path'
        return self.abspaths()[0]

    def relpath(self, applyStartDir = None):
        """
        Get relative path if kind == 'path'.
        This method is for convenience only.
        """

        assert self._kind == 'path'
        return self.relpaths(applyStartDir)[0]

    def __repr__(self):
        _repr = "%s(value = %r, startdir = %r, kind = %r)" % \
            (self._CLS_NAME, self._value, self._startdir, self._kind)
        return _repr

    def __eq__(self, other):
        if id(self) == id(other):
            return True
        if not isinstance(other, PathsParam):
            return False
        if self._kind != other._kind:
            return False
        if self._startdir == other._startdir:
            return self.relpaths() == other.relpaths()
        return self.abspaths() == other.abspaths()

    if PY2: # python 3 has it by default and it's more performant
        def __ne__(self, other):
            return not self == other

def makePathsDict(param, startdir):
    """
    Convert/Adjust param with paths/patterns to dict which is used in
    buildconf params, as storage for such paths in db, etc.
    """

    if isinstance(param, maptype):
        _startdir = param.get('startdir')
        if _startdir is not None:
            startdir = _normpath(_joinpath(startdir, _startdir))
        param['startdir'] = startdir
    else:
        val = param if isinstance(param, stringtype) else ' '.join(param)
        if any(x in val for x in ('*', '?')):
            # use as pattern
            param = { 'startdir' : startdir, 'include' : param }
        else:
            param = { 'startdir' : startdir, 'paths' : param }

    return param

def pathsDictParamsToList(paths):
    """
    Call 'toList' to all appropriate params of paths dict
    """

    for name in ('include', 'exclude', 'paths'):
        val = paths.get(name)
        if val is not None:
            paths[name] = toList(val)

def getNodesFromPathsDict(ctx, param, rootdir, withDirs = False, excludeExtraPaths = None):
    """
    Get list of Waf nodes from 'paths dict'.
    """

    if not param:
        return []

    startdir = _normpath(_joinpath(rootdir, param['startdir']))
    if not _isdir(startdir):
        raise ZenMakeDirNotFoundError(startdir)

    ctxPathNode = ctx.path
    ctxAbsPath = ctxPathNode.abspath()

    # Waf method Node.ant_glob can traverse both source and build folders, so
    # it is better to call this method only from the most specific node.
    # Also it is better, for performance, to use the ctx.path, not ctx.root
    if startdir == ctxAbsPath:
        startNode = ctxPathNode
    else:
        startNodeDir = _normpath(_relpath(startdir, ctxAbsPath))
        startNode = ctxPathNode.make_node(startNodeDir)

    files = param.get('paths')
    if files is None:
        include = param.get('include', [])
        exclude = list(param.get('exclude', []))
        exclude.extend(DEFAULT_PATH_EXCLUDES)

        if excludeExtraPaths:
            for path in excludeExtraPaths:
                if isinstance(path, stringtype):
                    path = ctx.root.make_node(path)
                if path.is_child_of(startNode):
                    pathPattern = path.path_from(startNode)
                    if os.sep == '\\':
                        pathPattern = pathPattern.replace('\\', '/')
                    exclude.append(pathPattern)
                    exclude.append(pathPattern + '/**')

        return startNode.ant_glob(
            incl = include,
            excl = exclude,
            ignorecase = param.get('ignorecase', False),
            dir = withDirs,
        )

    result = []
    for file in files:
        node = startNode if not _isabs(file) else ctx.root
        v = node.make_node(file)
        if not v.exists():
            raise ZenMakePathNotFoundError(v.abspath())
        result.append(v)

    return result
