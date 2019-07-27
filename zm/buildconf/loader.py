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
from copy import deepcopy
from zm import log, toolchains
from zm.constants import KNOWN_PLATFORMS
from zm.error import ZenMakeConfError, ZenMakeConfTypeError, ZenMakeConfValueError
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm.utils import loadPyModule
from zm.autodict import AutoDict as _AutoDict

KNOWN_TOOLCHAIN_KINDS = ['auto-' + lang \
                            for lang in toolchains.CompilersInfo.allLangs()]
KNOWN_TOOLCHAIN_KINDS += toolchains.CompilersInfo.allCompilers(platform = 'all')

class AnyAmountStrsKey(object):
    """ Any amount of string keys"""
    __slots__ = ()

    def __eq__(self, other):
        if not isinstance(other, AnyAmountStrsKey):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return True

    def __ne__(self, other):
        if not isinstance(other, AnyAmountStrsKey):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return False

    def __hash__(self):
        # necessary for instances to behave sanely in dicts and sets.
        return hash(self.__class__)

ANYAMOUNTSTRS_KEY = AnyAmountStrsKey()

confscheme = {
    'buildroot' : { 'type': 'str' },
    'buildsymlink' : { 'type': 'str' },
    'srcroot' : { 'type': 'str' },
    'features' : {
        'type' : 'dict',
        'vars' : {
            'autoconfig' : { 'type': 'bool' },
        },
    },
    'project' : {
        'type' : 'dict',
        'vars' : {
            'name' : { 'type': 'str' },
            'version' : { 'type': 'str' },
            'root' : { 'type': 'str' },
        },
    },
    'buildtypes' : {
        'type' : 'dict',
        'vars' : {
            ANYAMOUNTSTRS_KEY : {
                'type' : 'dict',
                'vars' : {
                    'toolchain' : {
                        'type': 'str',
                        'allowed' : KNOWN_TOOLCHAIN_KINDS,
                    },
                    'cflags' :    { 'type': ('str', 'list-of-strs') },
                    'cxxflags' :  { 'type': ('str', 'list-of-strs') },
                    'cppflags' :  { 'type': ('str', 'list-of-strs') },
                    'linkflags' : { 'type': ('str', 'list-of-strs') },
                    'defines' :   { 'type': ('str', 'list-of-strs') },
                },
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
            'valid' : { 'type': 'list-of-strs' },
            'default' : { 'type': 'str' },
        },
    },
    'tasks' : {
        'type' : 'vars-in-dict',
        'keys-kind' : 'anystr',
        'vars-type' : 'dict',
        'vars' : {
            'name' :        { 'type': 'str' },
            'features' :    { 'type': 'str' },
            'target' :      { 'type': 'str' },
            'sys-libs' :    { 'type': ('str', 'list-of-strs') },
            'sys-lib-path': { 'type': ('str', 'list-of-strs') },
            'rpath' :       { 'type': ('str', 'list-of-strs') },
            'use' :         { 'type': ('str', 'list-of-strs') },
            'ver-num' :     { 'type': 'str' },
            'includes':     { 'type': ('str', 'list-of-strs') },
            'source' :      {
                'type': ('str', 'list-of-strs', 'dict'),
                'dict-vars' : {
                    'include' :    { 'type': 'str' },
                    'exclude' :    { 'type': 'str' },
                    'ignorecase' : { 'type': 'bool' },
                },
            },
            'conftests' : {
                'type': 'list',
                'vars-type' : 'dict',
                'dict-vars' : {
                    'act' :        { 'type': 'str' },
                    'names' :      { 'type': ('str', 'list-of-strs') },
                    'mandatory' :  { 'type': 'bool' },
                    'autodefine' : { 'type': 'bool' },
                    'file' :       { 'type': 'str' },
                },
            },
        },
    },
}

confscheme['tasks']['vars'].update(
    confscheme['buildtypes']['vars'][ANYAMOUNTSTRS_KEY]['vars']
)
confscheme['tasks']['vars']['buildtypes'] = confscheme['buildtypes']

class Validator(object):
    """
    Validator for structure of buidconf.
    """

    __slots__ = ()

    _typeHandlerNames = {
        'bool' : '_handleBool',
        'str'  : '_handleStr',
        'dict' : '_handleDict',
        'list' : '_handleList',
        'complex' : '_handleComplex',
        'vars-in-dict' : '_handleVarsInDict',
        'list-of-strs' : '_handleListOfStrs',
    }

    @staticmethod
    def _getHandler(typeName):
        if isinstance(typeName, (list, tuple)):
            typeName = 'complex'
        return getattr(Validator, Validator._typeHandlerNames[typeName])

    @staticmethod
    def _checkStrKey(key, fullkey):
        if not isinstance(key, stringtype):
            msg = "Invalid type of key `%r`. In %r this key should be string." \
                % (key, fullkey)
            raise ZenMakeConfTypeError(msg)

    @staticmethod
    def _getAttrValue(attrs, key, typename, **kwargs):
        value = attrs.get(key, None)
        if value is None:
            value = attrs.get('%s-%s' % (typename, key), None)
        if value is None:
            if 'default' in kwargs:
                return kwargs['default']
            raise KeyError(key)
        return value

    @staticmethod
    def _handleComplex(confnode, schemeAttrs, fullkey):

        types = schemeAttrs['type']
        handlerArgs = (confnode, schemeAttrs, fullkey)

        for _type in types:
            try:
                Validator._getHandler(_type)(*handlerArgs)
            except ZenMakeConfTypeError:
                pass
            else:
                return

        typeNames = []
        for _type in types:
            if _type == 'str':
                typeNames.append('string')
            elif _type == 'list-of-strs':
                typeNames.append('list of strings')
            elif _type == 'dict':
                typeNames.append('dict/another map type')
            else:
                typeNames.append(_type)
        msg = "Invalid value `%r` for param %r." % (confnode, fullkey)
        msg += " It should be %s." % " or ".join(typeNames)
        raise ZenMakeConfTypeError(msg)

    @staticmethod
    def _handleBool(confnode, _, fullkey):
        if not isinstance(confnode, bool):
            msg = "Param %r should be bool" % fullkey
            raise ZenMakeConfTypeError(msg)

    @staticmethod
    def _handleStr(confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, stringtype):
            msg = "Param %r should be string" % fullkey
            raise ZenMakeConfTypeError(msg)
        if not schemeAttrs:
            return

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'str', default = None)
        if allowed is not None and confnode not in allowed:
            msg = "Invalid value `%r` for param %r." % (confnode, fullkey)
            msg = '%s Allowed values: %r' %(msg, allowed)
            raise ZenMakeConfValueError(msg)

    @staticmethod
    def _handleList(confnode, schemeAttrs, fullkey):
        def raiseInvalidTypeErr():
            msg = "Invalid value `%r` for param %r." % (confnode, fullkey)
            msg += " It should be list"
            raise ZenMakeConfTypeError(msg)

        if not isinstance(confnode, (list, tuple)):
            raiseInvalidTypeErr()

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'list', default = None)
        varsType = _getAttrValue(schemeAttrs, 'vars-type', 'list', default = None)

        if varsType:
            handler = Validator._getHandler(varsType)
        for i, elem in enumerate(confnode):
            if allowed is not None and elem not in allowed:
                msg = "Invalid value for param %r." % fullkey
                msg = '%s Allowed values: %r' %(msg, allowed)
                raise ZenMakeConfValueError(msg)
            if varsType:
                handler(elem, schemeAttrs, '%s.[%d]' % (fullkey, i))

    @staticmethod
    def _handleListOfStrs(confnode, schemeAttrs, fullkey):
        def raiseInvalidTypeErr():
            msg = "Invalid value `%r` for param %r." % (confnode, fullkey)
            msg += " It should be list of strings"
            raise ZenMakeConfTypeError(msg)

        if not isinstance(confnode, (list, tuple)):
            raiseInvalidTypeErr()

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'list-of-strs', default = None)
        for elem in confnode:
            if not isinstance(elem, stringtype):
                raiseInvalidTypeErr()
            if allowed is not None and elem not in allowed:
                msg = "Invalid value for param %r." % fullkey
                msg = '%s Allowed values: %r' %(msg, allowed)
                raise ZenMakeConfValueError(msg)

    @staticmethod
    def _handleDict(confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, maptype):
            msg = "Param %r should be dict or another map type." % fullkey
            raise ZenMakeConfTypeError(msg)

        _getAttrValue = Validator._getAttrValue
        subscheme = _getAttrValue(schemeAttrs, 'vars', 'dict')
        allowUnknownKeys = _getAttrValue(schemeAttrs, 'allow-unknown-keys',
                                         'dict', default = True)

        Validator._validate(confnode, subscheme, fullkey, allowUnknownKeys)

    @staticmethod
    def _handleVarsInDictWithKeysByList(confnode, schemeAttrs, fullkey):
        vartype = schemeAttrs['type']
        handler = Validator._getHandler(vartype)

        allowedKeys = schemeAttrs['keys-list']
        unknownKeys = set(confnode.keys()) - set(allowedKeys)
        if unknownKeys:
            unknownKeys = list(unknownKeys)
            if len(unknownKeys) == 1:
                msg = "Key %r isn't allowed in %r." % (unknownKeys[0], fullkey)
            else:
                msg = "Keys %r aren't allowed in %r." % (unknownKeys, fullkey)
            raise ZenMakeConfValueError(msg)

        for key in allowedKeys:
            _confnode = confnode.get(key, None)
            if _confnode is None:
                continue
            _fullkey = '.'.join((fullkey, key))
            handler(_confnode, schemeAttrs, _fullkey)

    @staticmethod
    def _handleVarsInDictWithKeysAnyStr(confnode, schemeAttrs, fullkey):
        vartype = schemeAttrs['type']
        handler = Validator._getHandler(vartype)

        for key, _confnode in viewitems(confnode):
            Validator._checkStrKey(key, fullkey)
            _fullkey = '.'.join((fullkey, key))
            handler(_confnode, schemeAttrs, _fullkey)

    @staticmethod
    def _handleVarsInDict(confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, maptype):
            msg = "Param %r should be dict or another map type." % fullkey
            raise ZenMakeConfTypeError(msg)

        vartype = schemeAttrs['vars-type']
        #_schemeAttrs = dict(schemeAttrs)
        _schemeAttrs = schemeAttrs
        _schemeAttrs['type'] = vartype

        if vartype == 'dict':
            for paramName in ('allow-unknown-keys', ):
                param = schemeAttrs.get('vars-%s' % paramName, None)
                if param is not None:
                    _schemeAttrs[paramName] = param

        keysKind = schemeAttrs['keys-kind']
        if keysKind == 'bylist':
            Validator._handleVarsInDictWithKeysByList(confnode, _schemeAttrs,
                                                      fullkey)
        elif keysKind == 'anystr':
            Validator._handleVarsInDictWithKeysAnyStr(confnode, _schemeAttrs,
                                                      fullkey)
        else:
            raise NotImplementedError

    @staticmethod
    def _validateUsualItems(conf, items, keyprefix):
        _handledKeys = []
        for key, schemeAttrs in items:
            confnode = conf.get(key, None)
            if confnode is None:
                continue
            typeName = schemeAttrs['type']
            fullKey = '.'.join((keyprefix, key))
            Validator._getHandler(typeName)(confnode, schemeAttrs, fullKey)
            _handledKeys.append(key)
        return _handledKeys

    @staticmethod
    def _validate(conf, scheme, keyprefix, allowUnknownKeys = True):

        _anyAmountStrsKey = None
        _usualItems = []
        for key, schemeAttrs in viewitems(scheme):
            if isinstance(key, AnyAmountStrsKey):
                _anyAmountStrsKey = key
            else:
                _usualItems.append((key, schemeAttrs))

        _handledKeys = Validator._validateUsualItems(conf, _usualItems, keyprefix)

        if _anyAmountStrsKey is None and allowUnknownKeys:
            return

        if _anyAmountStrsKey is not None:
            schemeAttrs = scheme[_anyAmountStrsKey]
            handler = Validator._getHandler(schemeAttrs['type'])

        for key, value in viewitems(conf):
            if key in _handledKeys:
                continue
            if _anyAmountStrsKey is not None and isinstance(key, stringtype):
                fullKey = '.'.join((keyprefix, key))
                handler(value, schemeAttrs, fullKey)
            elif not allowUnknownKeys:
                msg = "Unknown key `%r` for param %r." % (key, keyprefix)
                msg += " Unknown keys aren't allowed here."
                raise ZenMakeConfError(msg)

    def validate(self, conf, scheme):
        """
        Entry point for validation
        """

        _conf = _AutoDict(vars(conf))
        _scheme = deepcopy(scheme)

        btypesVars = _scheme['buildtypes']['vars']

        # set allowed values for buildtypes.'some name'.toolchain
        btypesNamed = btypesVars[ANYAMOUNTSTRS_KEY]['vars']
        if 'toolchains' in _conf and isinstance(_conf['toolchains'], maptype):
            btypesNamed['toolchain']['allowed'].extend(_conf['toolchains'].keys())

        # set allowed values for buildtypes.default
        allowed = []
        if 'buildtypes' in _conf and isinstance(_conf['buildtypes'], maptype):
            allowed.extend(_conf['buildtypes'].keys())
        if 'tasks' in _conf and isinstance(_conf['tasks'], maptype):
            for task in viewvalues(_conf['tasks']):
                buildtypes = task.get('buildtypes', {})
                allowed.extend(buildtypes.keys())

        if allowed:
            allowed = list(set(allowed))
            if 'default' in allowed:
                allowed.remove('default')
            btypesVars['default']['allowed'] = allowed

        self._validate(_conf, _scheme, conf.__name__)

def validate(buildconf):
    """
    Validate selected buildconf object
    """

    Validator().validate(buildconf, confscheme)

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

    # global vars
    if not hasattr(buildconf, 'buildroot'):
        setattr(buildconf, 'buildroot',
                os.path.join(buildconf.project['root'], 'build'))
    if not hasattr(buildconf, 'buildsymlink'):
        setattr(buildconf, 'buildsymlink', None)
    if not hasattr(buildconf, 'srcroot'):
        setattr(buildconf, 'srcroot', buildconf.project['root'])

def load(name = 'buildconf', dirpath = None, withImport = False, check = True):
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
        module = loadPyModule('zm.buildconf.fakeconf')

    try:
        if check:
            validate(module)
        initDefaults(module)
    except ZenMakeConfError as ex:
        if log.verbose() > 1:
            log.pprint('RED', ex.fullmsg) # pragma: no cover
        log.error(str(ex))
        sys.exit(1)

    return module
