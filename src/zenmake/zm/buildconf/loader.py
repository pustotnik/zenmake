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

from zm import log
from zm.constants import BUILDCONF_FILENAMES
from zm.error import ZenMakeConfError
from zm.pyutils import maptype, viewitems
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

def applyDefaults(buildconf):
    """
    Set default values to some params in buildconf if they don't exist
    """

    params = None

    # features
    if not hasattr(buildconf, 'features'):
        setattr(buildconf, 'features', {})
    params = buildconf.features
    params['autoconfig'] = params.get('autoconfig', True)

    # options
    if not hasattr(buildconf, 'options'):
        setattr(buildconf, 'options', {})

    # project
    if not hasattr(buildconf, 'project'):
        setattr(buildconf, 'project', {})
    params = buildconf.project
    params['root'] = params.get('root', os.curdir)
    params['name'] = params.get('name', None)
    if params['name'] is None:
        name = os.path.dirname(os.path.abspath(buildconf.__file__))
        name = os.path.basename(name)
        params['name'] = name
    params['version'] = params.get('version', '')

    # toolchains
    if not hasattr(buildconf, 'toolchains'):
        setattr(buildconf, 'toolchains', {})

    # platforms
    if not hasattr(buildconf, 'platforms'):
        setattr(buildconf, 'platforms', {})

    # buildtypes
    if not hasattr(buildconf, 'buildtypes'):
        setattr(buildconf, 'buildtypes', {})

    # tasks
    if not hasattr(buildconf, 'tasks'):
        setattr(buildconf, 'tasks', {})

    # matrix
    if not hasattr(buildconf, 'matrix'):
        setattr(buildconf, 'matrix', [])

    # global vars
    if not hasattr(buildconf, 'buildroot'):
        setattr(buildconf, 'buildroot',
                os.path.join(buildconf.project['root'], 'build'))

    # Param 'realbuildroot' must not be set here

    if not hasattr(buildconf, 'srcroot'):
        setattr(buildconf, 'srcroot', buildconf.project['root'])

def _loadYaml(filepath):
    try:
        import yaml
    except ImportError:
        errmsg = "Config file is yaml file but python module yaml"
        errmsg += " is not found. You should install it to use yaml buildconf file."
        errmsg += " You can do this for example with pip: pip install pyyaml"
        raise ZenMakeConfError(errmsg)

    try:
        from yaml import CSafeLoader as SafeLoader
    except ImportError:
        from yaml import SafeLoader

    import types
    buildconf = types.ModuleType('buildconf')
    buildconf.__file__ = os.path.abspath(filepath)
    data = {}
    with open(filepath, 'r') as stream:
        try:
            data = yaml.load(stream, SafeLoader)
        except yaml.YAMLError as ex:
            raise ZenMakeConfError(ex = ex)

    if not isinstance(data, maptype):
        raise ZenMakeConfError("File %r has invalid structure" % filepath)

    for k, v in viewitems(data):
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

def load(dirpath = None, filename = None, withDefaults = True, check = True):
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

    if check:
        validate(module)
    if withDefaults:
        applyDefaults(module)

    return module
