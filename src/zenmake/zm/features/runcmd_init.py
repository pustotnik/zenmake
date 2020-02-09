# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.pyutils import viewvalues
from zm.buildconf.schemeutils import ANYAMOUNTSTRS_KEY

VALIDATION_TASKSCHEME_SPEC = {
    'run' :       {
        'type' : 'dict',
        'allow-unknown-keys' : False,
        'vars' : {
            'cmd' : { 'type': ('str', 'func') },
            'cwd' : { 'type': 'str' },
            'env' : {
                'type': 'dict',
                'vars' : { ANYAMOUNTSTRS_KEY : { 'type': 'str' } },
            },
            'repeat' : { 'type': 'int' },
            'timeout' : { 'type': 'int' },
            'shell' : { 'type': 'bool' },
        },
    },
}

TASK_FEATURES_SETUP = {
    'runcmd' : {}
}

def detectFeatures(bconf):
    """
    Function for detect features in buildconfig.
    It's used by zm.features.loadFeatures.
    It should return a list of detected features.
    """

    for taskParams in viewvalues(bconf.tasks):
        if 'runcmd' in taskParams['features']:
            return ['runcmd']
        if 'run' in taskParams:
            return ['runcmd']

    return []
