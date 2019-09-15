# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

__all__ = [
    'validate',
    'initDefaults',
    'load',
]

import os
import sys

from zm import log
from zm.error import ZenMakeConfError
from zm.pyutils import maptype, viewitems
from zm.utils import loadPyModule
from zm.buildconf.validator import Validator as _Validator

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

def initDefaults(buildconf):
    """
    Set default values to some params in buildconf if they don't exist
    """

    params = None

    # features
    if not hasattr(buildconf, 'features'):
        setattr(buildconf, 'features', {})
    params = buildconf.features
    params['autoconfig'] = params.get('autoconfig', True)

    # project
    if not hasattr(buildconf, 'project'):
        setattr(buildconf, 'project', {})
    params = buildconf.project
    params['root'] = params.get('root', os.curdir)
    params['name'] = params.get('name', 'NONAME')
    params['version'] = params.get('version', '0.0.0.0')

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
    if not hasattr(buildconf, 'realbuildroot'):
        setattr(buildconf, 'realbuildroot', buildconf.buildroot)
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

def load(name = 'buildconf', dirpath = None, check = True):
    """
    Load buildconf.
    Param 'dirpath' is optional param that is used as directory
    with buildconf file.
    """

    isfile = os.path.isfile
    joinpath = os.path.join
    filenamePy = '%s.py' % name
    filenameYaml = '%s.yaml' % name
    found = None
    if not dirpath:
        # try to find config file
        for path in sys.path:
            if isfile(joinpath(path, filenamePy)):
                dirpath = path
                found = 'py'
                break
            if isfile(joinpath(path, filenameYaml)):
                dirpath = path
                found = 'yaml'
                break
    else:
        if isfile(joinpath(dirpath, filenamePy)):
            found = 'py'
        elif isfile(joinpath(dirpath, filenameYaml)):
            found = 'yaml'

    if found == 'py':
        # Avoid writing .pyc files
        sys.dont_write_bytecode = True
        module = loadPyModule(name, dirpath = dirpath, withImport = False)
        sys.dont_write_bytecode = False # pragma: no cover
    elif found == 'yaml':
        module = _loadYaml(joinpath(dirpath, filenameYaml))
    else:
        module = loadPyModule('zm.buildconf.fakeconf')

    if check:
        validate(module)
    initDefaults(module)

    return module
