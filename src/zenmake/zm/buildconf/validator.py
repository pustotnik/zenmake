# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from copy import deepcopy

from zm.error import ZenMakeConfError, ZenMakeConfTypeError, ZenMakeConfValueError
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm.utils import toList
from zm.autodict import AutoDict as _AutoDict
from zm.buildconf.scheme import confscheme, taskscheme, AnyAmountStrsKey, ANYAMOUNTSTRS_KEY

class Validator(object):
    """
    Validator for structure of buidconf.
    """

    __slots__ = ()

    _typeHandlerNames = {
        'bool' : '_handleBool',
        'int'  : '_handleInt',
        'str'  : '_handleStr',
        'dict' : '_handleDict',
        'list' : '_handleList',
        'func' : '_handleFunc',
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
            raise KeyError(key) # pragma: no cover
        return value

    @staticmethod
    def _handleComplex(confnode, schemeAttrs, fullkey):

        types = schemeAttrs['type']
        handlerArgs = (confnode, schemeAttrs, fullkey)
        valToList = False
        _types = types

        # special case
        if 'allowed' in schemeAttrs and sorted(types) == ['list-of-strs', 'str']:
            # this order of types is necessary
            _types = ('list-of-strs', 'str')
            valToList = True

        for _type in _types:
            if valToList and _type == 'list-of-strs':
                val = toList(confnode)
            else:
                val = confnode

            try:
                Validator._getHandler(_type)(val, schemeAttrs, fullkey)
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
    def _handleInt(confnode, _, fullkey):
        if not isinstance(confnode, int):
            msg = "Param %r should be integer" % fullkey
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

        _schemeAttrs = schemeAttrs
        if varsType:
            handler = Validator._getHandler(varsType)
            _schemeAttrs = dict(schemeAttrs)
            _schemeAttrs['type'] = varsType

        for i, elem in enumerate(confnode):
            if allowed is not None and elem not in allowed:
                msg = "Invalid value for param %r." % fullkey
                msg = '%s Allowed values: %r' %(msg, allowed)
                raise ZenMakeConfValueError(msg)
            if varsType:
                handler(elem, _schemeAttrs, '%s.[%d]' % (fullkey, i))

    @staticmethod
    def _handleFunc(confnode, _, fullkey):
        if not callable(confnode):
            msg = "Param %r should be function" % fullkey
            raise ZenMakeConfTypeError(msg)

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
            raise NotImplementedError # pragma: no cover

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
                msg += "\nValid values: %r" % sorted(scheme.keys())
                raise ZenMakeConfError(msg)

    def validate(self, conf):
        """
        Entry point for validation
        """

        #TODO: refactor this code

        _conf = _AutoDict(vars(conf))
        _scheme = deepcopy(confscheme)

        btypesVars = _scheme['buildtypes']['vars']

        # set allowed values for toolchain in tasks and buildtypes
        btypesNamed = btypesVars[ANYAMOUNTSTRS_KEY]['vars']
        if 'toolchains' in _conf and isinstance(_conf['toolchains'], maptype):
            # make copy of list
            allowed = list(taskscheme['toolchain']['allowed'])
            allowed.extend(_conf['toolchains'].keys())
            _scheme['tasks']['vars']['toolchain']['allowed'] = allowed
            btypesNamed['toolchain']['allowed'] = allowed

        # set allowed values for buildtypes.default
        allowed = []
        if 'buildtypes' in _conf and isinstance(_conf['buildtypes'], maptype):
            allowed.extend(_conf['buildtypes'].keys())
        if 'tasks' in _conf and isinstance(_conf['tasks'], maptype):
            for task in viewvalues(_conf['tasks']):
                if not isinstance(task, maptype):
                    continue
                buildtypes = task.get('buildtypes', {})
                allowed.extend(buildtypes.keys())

        if allowed:
            allowed = list(set(allowed))
            if 'default' in allowed:
                allowed.remove('default')
            btypesVars['default']['allowed'] = allowed

        try:
            self._validate(_conf, _scheme, conf.__name__)
        except ZenMakeConfError as ex:
            ex.msg = "Error in file %r:\n%s" % (conf.__file__, ex.msg)
            raise ex
