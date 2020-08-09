# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.error import ZenMakeConfError, ZenMakeConfTypeError, ZenMakeConfValueError
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm.utils import toList
from zm.autodict import AutoDict as _AutoDict
from zm.buildconf.schemeutils import AnyAmountStrsKey, ANYAMOUNTSTRS_KEY
from zm.buildconf.scheme import confscheme

class ZenMakeConfSubTypeError(ZenMakeConfTypeError):
    """Invalid buildconf param type error"""

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
        if not isinstance(typeName, stringtype):
            typeName = 'complex' if len(typeName) > 1 else typeName[0]
        return getattr(Validator, Validator._typeHandlerNames[typeName])

    @staticmethod
    def _checkStrKey(key, fullkey):
        if not isinstance(key, stringtype):
            msg = "Type of key `%r` is invalid. In %r this key should be string." \
                % (key, fullkey)
            raise ZenMakeConfTypeError(msg)

    @staticmethod
    def _getAttrValue(attrs, key, typename, **kwargs):
        value = attrs.get(key, attrs.get('%s-%s' % (typename, key), None))
        if value is None:
            if 'default' in kwargs:
                return kwargs['default']
            raise KeyError(key) # pragma: no cover
        return value

    @staticmethod
    def _handleComplex(confnode, schemeAttrs, fullkey):

        types = schemeAttrs['type']
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

            _schemeAttrs = schemeAttrs.get(_type, schemeAttrs)

            try:
                handler = Validator._getHandler(_type)
                handler(val, _schemeAttrs, fullkey)
            except ZenMakeConfSubTypeError:
                # it's an error from a sub type
                raise
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
        msg = "Value `%r` is invalid for the param %r." % (confnode, fullkey)
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
        if callable(allowed):
            allowed = allowed(confnode, fullkey)
        if allowed is not None and confnode not in allowed:
            msg = "Value `%r` is invalid for the param %r." % (confnode, fullkey)
            msg = '%s Allowed values: %s' %(msg, str(list(allowed))[1:-1])
            raise ZenMakeConfValueError(msg)

    @staticmethod
    def _handleList(confnode, schemeAttrs, fullkey):
        def raiseInvalidTypeErr(value):
            msg = "Value `%r` is invalid for the param %r." % (value, fullkey)
            msg += " It should be list"
            raise ZenMakeConfTypeError(msg)

        if not isinstance(confnode, (list, tuple)):
            raiseInvalidTypeErr(confnode)

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'list', default = None)
        varsType = _getAttrValue(schemeAttrs, 'vars-type', 'list', default = None)

        _schemeAttrs = schemeAttrs
        if varsType:
            handler = Validator._getHandler(varsType)
            _schemeAttrs = schemeAttrs.copy()
            _schemeAttrs['type'] = varsType

        if callable(allowed):
            allowed = allowed(confnode, fullkey)

        for i, elem in enumerate(confnode):
            if allowed is not None and elem not in allowed:
                msg = "Value %r is invalid for the param %r." % (elem, fullkey)
                msg = '%s Allowed values: %s' %(msg, str(list(allowed))[1:-1])
                raise ZenMakeConfValueError(msg)
            if varsType:
                try:
                    handler(elem, _schemeAttrs, '%s.[%d]' % (fullkey, i))
                except ZenMakeConfTypeError as ex:
                    raise ZenMakeConfSubTypeError(ex = ex)

    @staticmethod
    def _handleFunc(confnode, _, fullkey):
        if not callable(confnode):
            msg = "Param %r should be function" % fullkey
            raise ZenMakeConfTypeError(msg)

    @staticmethod
    def _handleListOfStrs(confnode, schemeAttrs, fullkey):
        def raiseInvalidTypeErr(value):
            msg = "Value `%r` is invalid for the param %r." % (value, fullkey)
            msg += " It should be list of strings"
            raise ZenMakeConfTypeError(msg)

        if not isinstance(confnode, (list, tuple)):
            raiseInvalidTypeErr(confnode)

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'list-of-strs', default = None)
        if callable(allowed):
            allowed = allowed(confnode, fullkey)
        for elem in confnode:
            if not isinstance(elem, stringtype):
                raiseInvalidTypeErr(elem)
            if allowed is not None and elem not in allowed:
                msg = "Value %r is invalid for the param %r." % (elem, fullkey)
                msg = '%s\nAllowed values: %s' %(msg, str(list(allowed))[1:-1])
                raise ZenMakeConfValueError(msg)

    @staticmethod
    def _handleDict(confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, maptype):
            msg = "Param %r should be dict or another map type." % fullkey
            raise ZenMakeConfTypeError(msg)

        _getAttrValue = Validator._getAttrValue
        subscheme = _getAttrValue(schemeAttrs, 'vars', 'dict', default = None)
        if subscheme is None:
            # don't validate keys
            return

        disallowedKeys = _getAttrValue(schemeAttrs, 'disallowed-keys',
                                       'dict', default = None)

        if disallowedKeys:
            allowUnknownKeys = False
        else:
            allowUnknownKeys = _getAttrValue(schemeAttrs, 'allow-unknown-keys',
                                             'dict', default = False)

        if callable(subscheme):
            subscheme = subscheme(confnode, fullkey)

        try:
            Validator._validate(confnode, subscheme, fullkey,
                                allowUnknownKeys, disallowedKeys)
        except ZenMakeConfTypeError as ex:
            raise ZenMakeConfSubTypeError(ex = ex)

    @staticmethod
    def _handleVarsInDict(confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, maptype):
            msg = "Param %r should be dict or another map type." % fullkey
            raise ZenMakeConfTypeError(msg)

        vartype = schemeAttrs.pop('vars-type')
        oldtype = schemeAttrs['type']
        if isinstance(oldtype, stringtype):
            schemeAttrs['type'] = 'dict'
        else:
            schemeAttrs['type'] = [ 'dict' if x == 'vars-in-dict' else x for x in oldtype ]

        dictAllowUnknownKeys = schemeAttrs.pop('vars-allow-unknown-keys', False)
        subvars = schemeAttrs.pop('vars')
        subscheme = {
            'type' : vartype,
            'vars' : subvars,
            'allow-unknown-keys' : dictAllowUnknownKeys,
        }

        keysKind = schemeAttrs.pop('keys-kind')
        if keysKind == 'anystr':
            for key, _confnode in viewitems(confnode):
                Validator._checkStrKey(key, fullkey)
            schemeAttrs['dict-vars'] = { ANYAMOUNTSTRS_KEY : subscheme }
        elif keysKind == 'bylist':
            allowedKeys = schemeAttrs.pop('keys-list')
            schemeAttrs['dict-vars'] = { k:subscheme for k in allowedKeys }
        else:
            raise NotImplementedError # pragma: no cover

        handler = Validator._getHandler(schemeAttrs['type'])
        handler(confnode, schemeAttrs, fullkey)

    @staticmethod
    def _genFullKey(keyprefix, key):
        return '.'.join((keyprefix, key)) if keyprefix else key

    @staticmethod
    def _validateUsualItems(conf, items, keyprefix):
        _handledKeys = []
        for key, schemeAttrs in items:
            confnode = conf.get(key, None)
            if confnode is None:
                continue
            fullKey = Validator._genFullKey(keyprefix, key)
            if callable(schemeAttrs):
                schemeAttrs = schemeAttrs(confnode, fullKey)
            typeName = schemeAttrs['type']
            Validator._getHandler(typeName)(confnode, schemeAttrs, fullKey)
            _handledKeys.append(key)
        return _handledKeys

    @staticmethod
    def _validate(conf, scheme, keyprefix, allowUnknownKeys = False, disallowedKeys = None):

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
            if callable(schemeAttrs):
                schemeAttrs = schemeAttrs(conf, keyprefix)
            handler = Validator._getHandler(schemeAttrs['type'])

        for key, value in viewitems(conf):
            if disallowedKeys and key in disallowedKeys:
                msg = "The key '%s' is not allowed in the param %r." % (str(key), keyprefix)
                raise ZenMakeConfError(msg)
            if key in _handledKeys:
                continue
            if _anyAmountStrsKey is not None and isinstance(key, stringtype):
                fullKey = Validator._genFullKey(keyprefix, key)
                handler(value, schemeAttrs, fullKey)
            elif not allowUnknownKeys:
                msg = "Unknown key '%s' is in the param %r." % (str(key), keyprefix)
                msg += " Unknown keys aren't allowed here."
                if _anyAmountStrsKey is not None:
                    msg += " Only string keys are valid."
                    raise ZenMakeConfTypeError(msg)

                msg += "\nValid values: %r" % sorted(scheme.keys())
                raise ZenMakeConfError(msg)

    def validate(self, conf):
        """
        Entry point for validation
        """

        #TODO: refactor this code

        _conf = _AutoDict(vars(conf))
        #_scheme = deepcopy(confscheme)
        _scheme = confscheme

        btypesVars = _scheme['buildtypes']['vars']

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
            allowed = set(allowed)
            if 'default' in allowed:
                allowed.remove('default')
            btypesVars['default']['allowed'] = allowed

        try:
            self._validate(_conf, _scheme, '', allowUnknownKeys = True)
        except ZenMakeConfError as ex:
            origMsg = ex.msg
            ex.msg = "Error in the file %r:" % (conf.__file__)
            for line in origMsg.splitlines():
                ex.msg += "\n  %s" % line
            raise ex
