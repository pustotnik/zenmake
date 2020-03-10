# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import KNOWN_PLATFORMS
from zm.pyutils import stringtype
from zm.cli import config as cliConfig
from zm.buildconf.schemeutils import ANYAMOUNTSTRS_KEY, addSelectToParams
from zm.features import ConfValidation

def _genSameSchemeDict(keys, scheme):
    return { k:scheme for k in keys }

def _genConfTestsScheme(confnode, fullkey):

    # pylint: disable = unused-argument

    # conf tests are in a list where each item has own scheme according 'act'
    scheme = {
        'type': 'list',
        'vars-type' : ('dict', 'func'),
        'dict-allow-unknown-keys' : False,
        'dict-vars' : _genConfTestsDictVarsScheme
    }

    return scheme

_actToVars = {
    'check-by-pyfunc' : {
        'func': { 'type': 'func' },
    },
    'check-programs' : {
        'names' : { 'type': ('str', 'list-of-strs') },
        'paths' : { 'type': ('str', 'list-of-strs') },
        'var':    { 'type': 'str' },
    },
    'check-headers' : {
        'names' :   { 'type': ('str', 'list-of-strs') },
        'defines' : { 'type': ('str', 'list-of-strs') },
    },
    'check-libs' : {
        'names' :      { 'type': ('str', 'list-of-strs') },
        'autodefine' : { 'type': 'bool' },
        'defines' :    { 'type': ('str', 'list-of-strs') },
    },
    'check-sys-libs' : {
        'autodefine' : { 'type': 'bool' },
        'defines' :    { 'type': ('str', 'list-of-strs') },
    },
    'check-code' : {
        'label' :   { 'type': 'str' },
        'text' :    { 'type': 'str' },
        'file' :    { 'type': 'str' },
        'defname' : { 'type': 'str' },
        'defines' : { 'type': ('str', 'list-of-strs') },
        'execute' : { 'type': 'bool' },
    },
    'parallel' : {
        'tryall' : { 'type': 'bool' },
        'checks' : _genConfTestsScheme,
    },
    'write-config-header' : {
        'file' : { 'type': 'str' },
        'guard': { 'type': 'str' },
    },
}

def _genConfTestsDictVarsScheme(confnode, fullkey):

    # common params for any conf test
    schemeDictVars = {
        'act' :       {
            'type': 'str',
            'allowed' : set(_actToVars.keys()),
        },
        'mandatory' : { 'type': 'bool' },
    }

    keyParts = fullkey.split('.')
    if keyParts[-2] == 'checks':
        # add specific params for parallel conf tests
        schemeDictVars.update({
            'id' :     { 'type': 'str' },
            'before' : { 'type': 'str' },
            'after' :  { 'type': 'str' },
        })

    act = confnode.get('act', '')
    if isinstance(act, stringtype):
        # add params specific for this act
        schemeDictVars.update(_actToVars.get(act, {}))
    return schemeDictVars

taskscheme = {
    'target' :      { 'type': 'str' },
    'features' :    { 'type': ('str', 'list-of-strs') },
    'use' :         { 'type': ('str', 'list-of-strs') },
    'source' :      {
        'type': ('str', 'list-of-strs', 'dict'),
        'dict-vars' : {
            'include' :    { 'type': ('str', 'list-of-strs') },
            'exclude' :    { 'type': ('str', 'list-of-strs') },
            'ignorecase' : { 'type': 'bool' },
        },
    },
    'toolchain' : { 'type': ('str', 'list-of-strs') },
    'install-path' : { 'type': ('bool', 'str') },
    'conftests' : _genConfTestsScheme,
    'normalize-target-name' : { 'type': 'bool' },
    'objfile-index' : { 'type': 'int' },
}

addSelectToParams(taskscheme, [x for x in taskscheme if x != 'features'])

taskscheme.update(ConfValidation.getTaskSchemeSpecs())

def _genOptionsVarsScheme(confnode, fullkey):

    # pylint: disable = unused-argument

    cmdNames = [ x.name for x in cliConfig.commands ]
    optNames = [ x.names[-1].replace('-', '', 2) for x in cliConfig.options ]

    optionsOptDictTypeScheme = _genSameSchemeDict(
        cmdNames + ['any'],
        { 'type' : ('bool', 'int', 'str'), }
    )

    scheme = _genSameSchemeDict(
        optNames,
        {
            'type' : ('bool', 'int', 'str', 'dict'),
            'allow-unknown-keys' : False,
            'dict-vars' : optionsOptDictTypeScheme,
        }
    )

    return scheme

confscheme = {
    'startdir' : { 'type': 'str' },
    'buildroot' : { 'type': 'str' },
    'realbuildroot' : { 'type': 'str' },
    'features' : {
        'type' : 'dict',
        'vars' : {
            'autoconfig' : { 'type': 'bool' },
            'monitor-files' : { 'type': ('str', 'list-of-strs') },
        },
    },
    'options' : {
        'type' : 'dict',
        'vars' : _genOptionsVarsScheme,
    },
    'subdirs' : {
        'type' : 'list-of-strs',
    },
    'project' : {
        'type' : 'dict',
        'vars' : {
            'name' : { 'type': 'str' },
            'version' : { 'type': 'str' },
        },
    },
    'conditions' : {
        'type' : 'dict',
        'disallowed-keys' : ('default', ),
        'vars' : {
            ANYAMOUNTSTRS_KEY : {
                #'type' : ('dict', 'func'),
                'type' : 'dict',
                'dict-vars' : {
                    'platform' :  { 'type': ('str', 'list-of-strs') },
                    'cpu-arch' :  { 'type': ('str', 'list-of-strs') },
                    'toolchain' : { 'type': ('str', 'list-of-strs') },
                    'task' :      { 'type': ('str', 'list-of-strs') },
                    'buildtype' : { 'type': ('str', 'list-of-strs') },
                    'environ' :   { 'type' : 'dict' },
                },
            },
        },
    },
    'tasks' : {
        'type' : 'vars-in-dict',
        'keys-kind' : 'anystr',
        'vars-type' : 'dict',
        'vars-allow-unknown-keys' : False,
        'vars' : taskscheme,
    },
    'buildtypes' : {
        'type' : 'dict',
        'vars' : {
            ANYAMOUNTSTRS_KEY : {
                'type' : 'dict',
                'vars' : taskscheme,
            },
            'default' : { 'type': 'str' },
        },
    },
    'toolchains' : {
        'type' : 'vars-in-dict',
        'keys-kind' : 'anystr',
        'vars-type' : 'dict',
        'vars-allow-unknown-keys' : False,
        'vars' : {
            'kind' : { 'type': 'str' },
            ANYAMOUNTSTRS_KEY : { 'type' : 'str' },
        },
    },
    'platforms' : {
        'type' : 'vars-in-dict',
        'keys-kind' : 'bylist',
        'keys-list' : KNOWN_PLATFORMS,
        'vars-type' : 'dict',
        'vars' : {
            'valid' : { 'type': ('str', 'list-of-strs') },
            'default' : { 'type': 'str' },
        },
    },
    'matrix' : {
        'type' : 'list',
        'vars-type' : 'dict',
        'dict-allow-unknown-keys' : False,
        'dict-vars' : {
            'for' : {
                'type': 'dict',
                'vars' : {
                    'task' : { 'type': ('str', 'list-of-strs') },
                    'buildtype' : { 'type': ('str', 'list-of-strs') },
                    'platform' : { 'type': ('str', 'list-of-strs') },
                },
            },
            'not-for' : {
                'type': 'dict',
                'vars' : {
                    'task' : { 'type': ('str', 'list-of-strs') },
                    'buildtype' : { 'type': ('str', 'list-of-strs') },
                    'platform' : { 'type': ('str', 'list-of-strs') },
                },
            },
            'set' : {
                'type' : 'dict',
                'vars' : dict(
                    { 'default-buildtype' : { 'type': 'str' } },
                    **taskscheme
                ),
            },
        },
    },
}

KNOWN_TASK_PARAM_NAMES = frozenset(taskscheme.keys())
KNOWN_CONF_PARAM_NAMES = frozenset(confscheme.keys())
KNOWN_CONDITION_PARAM_NAMES = \
    frozenset(confscheme['conditions']['vars'][ANYAMOUNTSTRS_KEY]['dict-vars'].keys())
KNOWN_CONFTEST_ACTS = frozenset(_actToVars.keys())
