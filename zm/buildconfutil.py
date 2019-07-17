# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
from zm import log
from zm.error import ZenMakeError
from zm.utils import loadPyModule

def validateAll(buildconf):
    """
    Validate selected buildconf object
    """

    if not buildconf.tasks:
        raise ZenMakeError("No tasks were found in buildconf.")

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
        buildconf.buildtypes['debug'] = {}
        buildconf.buildtypes['default'] = 'debug'

    # tasks
    if not hasattr(buildconf, 'tasks'):
        setattr(buildconf, 'tasks', {})

    # global vars
    if not hasattr(buildconf, 'buildroot'):
        setattr(buildconf, 'buildroot',
                os.path.join(buildconf.project['root'], 'build'))
    if not hasattr(buildconf, 'buildsymlink'):
        setattr(buildconf, 'buildsymlink', None)
    if not hasattr(buildconf, 'srcroot'):
        setattr(buildconf, 'srcroot', buildconf.project['root'])

def loadConf(name = 'buildconf', dirpath = None, withImport = False):
    """
    Load buildconf
    Params 'dirpath' and 'withImport' are the params for zm.utils.loadPyModule
    """

    try:
        # Avoid writing .pyc files
        sys.dont_write_bytecode = True
        module = loadPyModule(name, dirpath = dirpath, withImport = withImport)
        sys.dont_write_bytecode = False # pragma: no cover
    except ImportError:
        module = loadPyModule('zm.fakebuildconf')

    try:
        initDefaults(module)
        validateAll(module)
    except ZenMakeError as ex:
        if log.verbose() > 1:
            log.pprint('RED', ex.fullmsg) # pragma: no cover
        log.error(str(ex))
        sys.exit(1)

    return module
