# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

__all__ = [
    'validate',
    'applyDefaults',
    'load',
]

import os
import sys
import io
import types

from zm import log
from zm.constants import BUILDCONF_FILENAMES, DEFAULT_BUILDROOTNAME
from zm.error import ZenMakeConfError
from zm.pyutils import maptype
from zm.utils import loadPyModule
from zm.buildconf.validator import Validator as _Validator

isfile = os.path.isfile
joinpath = os.path.join

def validate(buildconf):
    """
    Validate selected buildconf object
    """

    try:
        _Validator().validate(buildconf)
    except ZenMakeConfError as ex:
        if log.verbose() > 1:
            log.pprint('RED', ex.fullmsg) # pragma: no cover
        log.error(str(ex))
        sys.exit(1)

def applyDefaults(buildconf, isTopLevel, projectDir):
    """
    Set default values to some params in buildconf if they don't exist
    """

    params = None

    # Param 'startdir' is set in another place

    # buildroot
    if isTopLevel:
        if not hasattr(buildconf, 'buildroot'):
            setattr(buildconf, 'buildroot', DEFAULT_BUILDROOTNAME)

    # Param 'realbuildroot' must not be set here

    # features
    if not hasattr(buildconf, 'features'):
        setattr(buildconf, 'features', {})
    if isTopLevel:
        params = buildconf.features
        params['autoconfig'] = params.get('autoconfig', True)
        params['hash-algo'] = params.get('hash-algo', 'sha1')
        params['db-format'] = params.get('db-format', 'pickle')

    # dict params
    dictParams = (
        'options', 'conditions', 'edeps', 'toolchains',
        'platforms', 'buildtypes', 'tasks'
    )
    for param in dictParams:
        if not hasattr(buildconf, param):
            setattr(buildconf, param, {})

    # usedirs
    if not hasattr(buildconf, 'subdirs'):
        setattr(buildconf, 'subdirs', [])

    # project
    if not hasattr(buildconf, 'project'):
        setattr(buildconf, 'project', {})
    if isTopLevel:
        params = buildconf.project
        params['name'] = params.get('name', None)
        if params['name'] is None:
            params['name'] = os.path.basename(projectDir)
        params['version'] = params.get('version', '')

    # byfilter
    if not hasattr(buildconf, 'byfilter'):
        setattr(buildconf, 'byfilter', [])

def _loadYaml(filepath):
    try:
        import yaml
    except ImportError:
        from auxiliary.pyyaml import yaml

    try:
        yamlLoader = yaml.CSafeLoader
    except AttributeError:
        yamlLoader = yaml.SafeLoader

    buildconf = types.ModuleType('buildconf')
    buildconf.__file__ = os.path.abspath(filepath)
    data = {}
    with io.open(filepath, 'rt', encoding = 'utf-8') as stream:
        try:
            data = yaml.load(stream, yamlLoader)
        except yaml.YAMLError as ex:
            raise ZenMakeConfError(ex = ex) from ex

    if not isinstance(data, maptype):
        raise ZenMakeConfError("File %r has invalid structure" % filepath)

    for k, v in data.items():
        setattr(buildconf, k, v)
    return buildconf

def findConfFile(dpath, fname = None):
    """
    Try to find buildconf file.
    Returns filename if found or None
    """
    if fname:
        if isfile(joinpath(dpath, fname)):
            return fname
        return None

    for name in BUILDCONF_FILENAMES:
        if isfile(joinpath(dpath, name)):
            return name
    return None

def load(dirpath = None, filename = None):
    """
    Load buildconf.
    Param 'dirpath' is optional param that is used as directory
    with buildconf file.
    """

    if not dirpath:
        # try to find config file
        for path in sys.path:
            _filename = findConfFile(path, filename)
            if _filename:
                dirpath = path
                filename = _filename
                break
        else:
            filename = None
    else:
        filename = findConfFile(dirpath, filename)

    found = None
    if filename:
        found = 'py' if filename.endswith('.py') else 'yaml'

    if found == 'py':
        # Avoid writing .pyc files
        sys.dont_write_bytecode = True
        module = loadPyModule(filename[:-3], dirpath = dirpath, withImport = False)
        sys.dont_write_bytecode = False # pragma: no cover
    elif found == 'yaml':
        module = _loadYaml(joinpath(dirpath, filename))
    else:
        module = loadPyModule('zm.buildconf.fakeconf')

    return module
