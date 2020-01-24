# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm import toolchains
from zm.constants import KNOWN_PLATFORMS
from zm.pyutils import stringtype
from zm.cli import COMMAND_NAMES, OPTION_NAMES

KNOWN_TOOLCHAIN_KINDS = ['auto-' + lang \
                            for lang in toolchains.CompilersInfo.allLangs()]
KNOWN_TOOLCHAIN_KINDS += toolchains.CompilersInfo.allCompilers(platform = 'all')

class AnyAmountStrsKey(object):
    """ Any amount of string keys"""
    __slots__ = ()

    def __eq__(self, other):
        if not isinstance(other, AnyAmountStrsKey):
            # don't attempt to compare against unrelated types
            return NotImplemented # pragma: no cover
        return True

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash(self.__class__)

ANYAMOUNTSTRS_KEY = AnyAmountStrsKey()

def _genSameSchemeDict(keys, scheme):
    return { k:scheme for k in keys }

def _genConfTestsScheme(confnode, fullkey):

    # pylint: disable = unused-argument

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

    schemeDictVars = {
        'act' :       {
            'type': 'str',
            'allowed' : set(_actToVars.keys()),
        },
        'mandatory' : { 'type': 'bool' },
    }

    if fullkey.split('.')[-2] == 'checks':
        schemeDictVars.update({
            'id' :     { 'type': 'str' },
            'before' : { 'type': 'str' },
            'after' :  { 'type': 'str' },
        })

    act = confnode.get('act', '')
    if isinstance(act, stringtype):
        schemeDictVars.update(_actToVars.get(act, {}))
    return schemeDictVars

taskscheme = {
    'target' :      { 'type': 'str' },
    'features' :    { 'type': ('str', 'list-of-strs') },
    'sys-libs' :    { 'type': ('str', 'list-of-strs') },
    'libpath':      { 'type': ('str', 'list-of-strs') },
    'rpath' :       { 'type': ('str', 'list-of-strs') },
    'use' :         { 'type': ('str', 'list-of-strs') },
    'ver-num' :     { 'type': 'str' },
    'includes':     { 'type': ('str', 'list-of-strs') },
    'source' :      {
        'type': ('str', 'list-of-strs', 'dict'),
        'dict-allow-unknown-keys' : False,
        'dict-vars' : {
            'include' :    { 'type': 'str' },
            'exclude' :    { 'type': 'str' },
            'ignorecase' : { 'type': 'bool' },
        },
    },
    'toolchain' : {
        'type': ('str', 'list-of-strs'),
        'allowed' : KNOWN_TOOLCHAIN_KINDS,
    },
    'asflags' :   { 'type': ('str', 'list-of-strs') },
    'aslinkflags' : { 'type': ('str', 'list-of-strs') },
    'cflags' :    { 'type': ('str', 'list-of-strs') },
    'cxxflags' :  { 'type': ('str', 'list-of-strs') },
    'cppflags' :  { 'type': ('str', 'list-of-strs') },
    'linkflags' : { 'type': ('str', 'list-of-strs') },
    'defines' :   { 'type': ('str', 'list-of-strs') },
    'export-includes' : { 'type': ('bool', 'str', 'list-of-strs') },
    'export-defines' :  { 'type': ('bool', 'str', 'list-of-strs') },
    'install-path' : { 'type': ('bool', 'str') },
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
    'conftests' : _genConfTestsScheme,
    'normalize-target-name' : { 'type': 'bool' },
    'object-file-counter' : { 'type': 'int' },
}

_optionsOptDictTypeScheme = _genSameSchemeDict(list(COMMAND_NAMES) + ['any'], {
    'type' : ('bool', 'int', 'str'),
})

_optionsOptScheme = _genSameSchemeDict(OPTION_NAMES, {
    'type' : ('bool', 'int', 'str', 'dict'),
    'allow-unknown-keys' : False,
    'dict-vars' : _optionsOptDictTypeScheme,
})

confscheme = {
    'startdir' : { 'type': 'str' },
    'buildroot' : { 'type': 'str' },
    'realbuildroot' : { 'type': 'str' },
    'features' : {
        'type' : 'dict',
        'allow-unknown-keys' : False,
        'vars' : {
            'autoconfig' : { 'type': 'bool' },
            'monitor-files' : { 'type': ('str', 'list-of-strs') },
        },
    },
    'options' : {
        'type' : 'dict',
        'allow-unknown-keys' : False,
        'vars' : _optionsOptScheme,
    },
    'subdirs' : {
        'type' : 'list-of-strs',
    },
    'project' : {
        'type' : 'dict',
        'allow-unknown-keys' : False,
        'vars' : {
            'name' : { 'type': 'str' },
            'version' : { 'type': 'str' },
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
                'allow-unknown-keys' : False,
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
            'kind' : {
                'type': 'str',
                'allowed' : KNOWN_TOOLCHAIN_KINDS,
            },
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
                'allow-unknown-keys' : False,
                'vars' : {
                    'task' : { 'type': ('str', 'list-of-strs') },
                    'buildtype' : { 'type': ('str', 'list-of-strs') },
                    'platform' : { 'type': ('str', 'list-of-strs') },
                },
            },
            'not-for' : {
                'type': 'dict',
                'allow-unknown-keys' : False,
                'vars' : {
                    'task' : { 'type': ('str', 'list-of-strs') },
                    'buildtype' : { 'type': ('str', 'list-of-strs') },
                    'platform' : { 'type': ('str', 'list-of-strs') },
                },
            },
            'set' : {
                'type' : 'dict',
                'allow-unknown-keys' : False,
                'vars' : dict(
                    { 'default-buildtype' : { 'type': 'str' } },
                    **taskscheme
                ),
            },
        },
    },
}

KNOWN_TASK_PARAM_NAMES = set(taskscheme.keys())
KNOWN_CONF_PARAM_NAMES = set(confscheme.keys())
KNOWN_CONFTEST_ACTS = set(_actToVars.keys())
