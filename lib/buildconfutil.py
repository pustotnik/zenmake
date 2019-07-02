# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD, see LICENSE for more details.
"""

import os
import sys
from waflib import Logs
from waflib.Errors import WafError
import utils

if not Logs.log:
    Logs.init_log()

def validateAll(buildconf):

    if not buildconf.tasks:
        raise WafError("No tasks were found in buildconf.")

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
    params['root'] = params.get('root', '.')
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

    # global vars
    if not hasattr(buildconf, 'buildroot'):
        setattr(buildconf, 'buildroot', 'build')
    if not hasattr(buildconf, 'buildsymlink'):
        setattr(buildconf, 'buildsymlink', None)
    if not hasattr(buildconf, 'srcroot'):
        setattr(buildconf, 'srcroot', '.')

def loadConf():
    try:
        # Avoid writing .pyc files
        sys.dont_write_bytecode = True
        module = utils.loadPyModule('buildconf')
        sys.dont_write_bytecode = False
    except ImportError:
        module = utils.loadPyModule('fakebuildconf')
    
    try:
        initDefaults(module)
        validateAll(module)
    except WafError as e:
		if Logs.verbose > 1:
			Logs.pprint('RED', e.verbose_msg)
		Logs.error(str(e))
		sys.exit(1)

    return module