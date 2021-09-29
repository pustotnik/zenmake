# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from waflib.Node import exclude_regs as DEFAULT_PATH_EXCLUDES
from waflib import Utils as wafutils
from zm.pyutils import maptype, stringtype
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

_pathPatternsCache = {}

splitPath = wafutils.split_path

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

        if isinstance(value, PathsParam):
            self._makeFrom(value, startdir, rootdir, kind)
            return

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

    def _makeFrom(self, pathsParam, startdir = None, rootdir = None, kind = None):
        """ Make the new object as a copy of pathsParam """

        # pylint: disable = protected-access

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

    @classmethod
    def makeFrom(cls, pathsParam, startdir = None, rootdir = None, kind = None):
        """ Make the new object as a copy of pathsParam """

        self = cls.__new__(cls)
        return self._makeFrom(pathsParam, startdir, rootdir, kind)

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

def pathsDictParamsToList(item):
    """
    Call 'toList' to all appropriate params of paths conf dict item
    """

    for name in ('incl', 'excl', 'paths'):
        val = item.get(name)
        if val is not None:
            item[name] = toList(val)

def makePathsConf(param, startdir):
    """
    Convert/Adjust param with paths/patterns to list of dicts which is used in
    buildconf params, as storage for such paths in db, etc.
    Param 'startdir' must be absolute or relative to rootdir
    """

    if not param:
        return []

    if isinstance(param, stringtype):
        param = toList(param)
    elif isinstance(param, maptype):
        param = [param]
    else:
        # avoid conversion of already processed param
        if isinstance(param[0], maptype) and '*ready*' in param[0]:
            return param

        items = []
        for item in param:
            subitems = toList(item) if isinstance(item, stringtype) else [item]
            items.extend(subitems)
        param = items

    result = []
    paths = []
    for item in param:

        if isinstance(item, maptype):
            item.setdefault('startdir', startdir)
            pathsDictParamsToList(item)
            result.append(item)
            continue

        assert isinstance(item, stringtype)

        if not any(x in item for x in ('*', '?')):
            # use as a path
            paths.append(item)
            continue

        # use as a pattern
        result.append({ 'startdir' : startdir, 'incl': [item] })

    if paths:
        # gather all paths in one item
        result.append({ 'startdir' : startdir, 'paths' : paths })

    result[0]['*ready*'] = 1 # marker about finished work
    return result

def _getNodesFromPathPatterns(ctx, param, startNode, withDirs,
                              excludeExtraPaths, cache):

    # pylint: disable = too-many-arguments

    if not ('incl' in param or 'excl' in param):
        return []

    include = param.get('incl', '**')

    if cache:
        cacheKey = repr(sorted(param.items()))
        cached = _pathPatternsCache.get(cacheKey)
        if cached is not None:
            return [ctx.root.make_node(x) for x in cached]

    exclude = list(param.get('excl', []))
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

    nodes = startNode.ant_glob(
        incl = include,
        excl = exclude,
        ignorecase = param.get('ignorecase', False),
        dir = withDirs,
        generator = not cache,
        remove = False, # don't remove declared paths
    )

    if cache:
        _pathPatternsCache[cacheKey] = [x.abspath() for x in nodes]

    return nodes

def getNodesFromPathsConf(ctx, param, rootdir, withDirs = False,
                          excludeExtraPaths = None, cache = False, onNoPath = None):
    """
    Get list of Waf nodes from 'paths config'.
    """

    # pylint: disable = too-many-arguments

    if not param:
        # stop iteration
        return

    if not isinstance(param, (list, tuple)):
        param = [param]

    def doNoPathError(excCls, arg):
        ex = excCls(arg)
        if onNoPath:
            onNoPath(ex)
        else:
            raise ex

    ctxPathNode = ctx.path
    ctxAbsPath = ctxPathNode.abspath()

    try:
        btypeNode = ctx.bldnode.parent if ctx.buildWorkDirName else ctx.bldnode
    except AttributeError:
        btypeNode = None

    for item in param:

        startdir = _normpath(_joinpath(rootdir, item['startdir']))

        if not _isdir(startdir):
            doNoPathError(ZenMakeDirNotFoundError, startdir)
            return

        # Waf method Node.ant_glob can traverse both source and build folders, so
        # it is better to call this method only from the most specific node.
        # Also it is better, for performance, to use the ctx.path, not ctx.root
        if startdir == ctxAbsPath:
            startNode = ctxPathNode
        else:
            startNodeDir = _normpath(_relpath(startdir, ctxAbsPath))
            startNode = ctxPathNode.make_node(startNodeDir)

        nodes = _getNodesFromPathPatterns(ctx, item, startNode, withDirs,
                                          excludeExtraPaths, cache)

        for node in nodes:
            yield node

        paths = item.get('paths', [])
        if not paths:
            continue

        # There is no reasons to cache lists of paths and
        # the cache key for them can be too big

        for path in paths:
            isRelative = not _isabs(path)
            snode = startNode if isRelative else ctx.root
            splittedPath = [x for x in splitPath(path) if x and x != '.']

            node = snode.find_node(splittedPath)
            if not node and btypeNode and isRelative:
                # try to find declared node in build dir
                # it can be 'target' from standalone runcmd task
                node = btypeNode.search_node(splittedPath)
            if not node:
                doNoPathError(ZenMakePathNotFoundError, path)
                return

            yield node
