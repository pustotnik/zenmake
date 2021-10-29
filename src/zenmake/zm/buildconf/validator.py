# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from copy import deepcopy

from zm.error import ZenMakeConfError, ZenMakeConfTypeError, ZenMakeConfValueError
from zm.pyutils import maptype, stringtype
from zm.utils import toList
from zm.buildconf.schemeutils import ANYSTR_KEY
from zm.buildconf.scheme import confscheme

# for checks
_oldconfscheme = deepcopy(confscheme)

class ZenMakeConfSubTypeError(ZenMakeConfTypeError):
    """Invalid buildconf param type error"""

class Validator(object):
    """
    Validator for structure of buidconf.
    """

    __slots__ = ('_conf', )

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

    def __init__(self, buildconf):
        self._conf = vars(buildconf)

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

    def _handleComplex(self, confnode, schemeAttrs, fullkey):

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
                handler(self, val, _schemeAttrs, fullkey)
            except ZenMakeConfSubTypeError:
                # it's an error from a sub type
                raise
            except ZenMakeConfTypeError:
                pass
            else:
                return

        typeswitch = {
            'str'         : 'string',
            'list-of-strs': 'list of strings',
            'dict'        : 'dict/another map type',
        }
        typeNames = [ typeswitch.get(_type, _type) for _type in types ]

        msg = "Value `%r` is invalid for the param %r." % (confnode, fullkey)
        msg += " It should be %s." % " or ".join(typeNames)
        raise ZenMakeConfTypeError(msg)

    def _handleBool(self, confnode, _, fullkey):
        if not isinstance(confnode, bool):
            msg = "Param %r should be bool" % fullkey
            raise ZenMakeConfTypeError(msg)

    def _handleInt(self, confnode, _, fullkey):
        if not isinstance(confnode, int):
            msg = "Param %r should be integer" % fullkey
            raise ZenMakeConfTypeError(msg)

    def _handleStr(self, confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, stringtype):
            msg = "Param %r should be string" % fullkey
            raise ZenMakeConfTypeError(msg)
        if not schemeAttrs:
            return

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'str', default = None)
        if callable(allowed):
            allowed = allowed(self._conf, confnode, fullkey)
        if allowed is not None and confnode not in allowed:
            msg = "Value `%r` is invalid for the param %r." % (confnode, fullkey)
            msg = '%s Allowed values: %s' %(msg, str(list(allowed))[1:-1])
            raise ZenMakeConfValueError(msg)

    def _handleList(self, confnode, schemeAttrs, fullkey):
        def raiseInvalidTypeErr(value):
            msg = "Value `%r` is invalid for the param %r." % (value, fullkey)
            msg += " It should be list"
            raise ZenMakeConfTypeError(msg)

        if not isinstance(confnode, (list, tuple)):
            raiseInvalidTypeErr(confnode)

        schemeAttrs = schemeAttrs.get('list', schemeAttrs)

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'list', default = None)
        varsType = _getAttrValue(schemeAttrs, 'vars-type', 'list', default = None)

        _schemeAttrs = schemeAttrs
        if varsType:
            handler = Validator._getHandler(varsType)
            _schemeAttrs = schemeAttrs.copy()
            _schemeAttrs['type'] = varsType

        if callable(allowed):
            allowed = allowed(self._conf, confnode, fullkey)

        for i, elem in enumerate(confnode):
            if allowed is not None and elem not in allowed:
                msg = "Value %r is invalid for the param %r." % (elem, fullkey)
                msg = '%s Allowed values: %s' %(msg, str(list(allowed))[1:-1])
                raise ZenMakeConfValueError(msg)
            if varsType:
                try:
                    handler(self, elem, _schemeAttrs, '%s.[%d]' % (fullkey, i))
                except ZenMakeConfTypeError as ex:
                    raise ZenMakeConfSubTypeError(ex = ex) from ex

    def _handleFunc(self, confnode, _, fullkey):
        if not callable(confnode):
            msg = "Param %r should be function" % fullkey
            raise ZenMakeConfTypeError(msg)

    def _handleListOfStrs(self, confnode, schemeAttrs, fullkey):
        def raiseInvalidTypeErr(value):
            msg = "Value `%r` is invalid for the param %r." % (value, fullkey)
            msg += " It should be list of strings"
            raise ZenMakeConfTypeError(msg)

        if not isinstance(confnode, (list, tuple)):
            raiseInvalidTypeErr(confnode)

        _getAttrValue = Validator._getAttrValue
        allowed = _getAttrValue(schemeAttrs, 'allowed', 'list-of-strs', default = None)
        if callable(allowed):
            allowed = allowed(self._conf, confnode, fullkey)
        for elem in confnode:
            if not isinstance(elem, stringtype):
                raiseInvalidTypeErr(elem)
            if allowed is not None and elem not in allowed:
                msg = "Value %r is invalid for the param %r." % (elem, fullkey)
                msg = '%s\nAllowed values: %s' %(msg, str(list(allowed))[1:-1])
                raise ZenMakeConfValueError(msg)

    def _handleDict(self, confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, maptype):
            msg = "Param %r should be dict or another map type." % fullkey
            raise ZenMakeConfTypeError(msg)

        schemeAttrs = schemeAttrs.get('dict', schemeAttrs)

        _getAttrValue = Validator._getAttrValue
        subscheme = _getAttrValue(schemeAttrs, 'vars', 'dict', default = None)
        if subscheme is None:
            # don't validate keys
            return

        allowedKeys = _getAttrValue(schemeAttrs, 'allowed-keys',
                                       'dict', default = None)

        if allowedKeys:
            allowUnknownKeys = False
        else:
            allowUnknownKeys = _getAttrValue(schemeAttrs, 'allow-unknown-keys',
                                             'dict', default = False)

        if callable(subscheme):
            subscheme = subscheme(confnode, fullkey)

        try:
            self._process(confnode, subscheme, fullkey,
                                allowUnknownKeys, allowedKeys)
        except ZenMakeConfTypeError as ex:
            raise ZenMakeConfSubTypeError(ex = ex) from ex

    def _handleVarsInDict(self, confnode, schemeAttrs, fullkey):
        if not isinstance(confnode, maptype):
            msg = "Param %r should be dict or another map type." % fullkey
            raise ZenMakeConfTypeError(msg)

        # it's better not to change the origin conf scheme
        schemeAttrs = schemeAttrs.copy()
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
            for key, _confnode in confnode.items():
                Validator._checkStrKey(key, fullkey)
            schemeAttrs['dict-vars'] = { ANYSTR_KEY : subscheme }
        elif keysKind == 'bylist':
            allowedKeys = schemeAttrs.pop('keys-list')
            schemeAttrs['dict-vars'] = { k:subscheme for k in allowedKeys }
        else:
            raise NotImplementedError # pragma: no cover

        handler = Validator._getHandler(schemeAttrs['type'])
        handler(self, confnode, schemeAttrs, fullkey)

    @staticmethod
    def _genFullKey(keyprefix, key):
        return '.'.join((keyprefix, key)) if keyprefix else key

    def _processItems(self, conf, items, keyprefix):
        _handledKeys = []
        for key, schemeAttrs in items:
            confnode = conf.get(key, None)
            if confnode is None:
                continue
            fullKey = Validator._genFullKey(keyprefix, key)
            if callable(schemeAttrs):
                schemeAttrs = schemeAttrs(confnode, fullKey)
            typeName = schemeAttrs['type']
            Validator._getHandler(typeName)(self, confnode, schemeAttrs, fullKey)
            _handledKeys.append(key)
        return _handledKeys

    def _process(self, conf, scheme, keyprefix, allowUnknownKeys = False, allowedKeys = None):

        # pylint: disable = too-many-branches

        scheme = scheme.copy()
        _anyStrScheme = scheme.pop(ANYSTR_KEY, None)
        _anyStrKeyExists = _anyStrScheme is not None

        _handledKeys = self._processItems(conf, scheme.items(), keyprefix)

        if not _anyStrKeyExists and allowUnknownKeys:
            return

        if _anyStrKeyExists:
            schemeAttrs = _anyStrScheme
            if callable(schemeAttrs):
                schemeAttrs = schemeAttrs(conf, keyprefix)
            handler = Validator._getHandler(schemeAttrs['type'])

        for key, value in conf.items():
            if allowedKeys:
                if callable(allowedKeys):
                    allowedKeys(self._conf, key, keyprefix)
                elif key not in allowedKeys:
                    msg = "The key '%s' is not allowed in the param %r." % (str(key), keyprefix)
                    raise ZenMakeConfError(msg)
            if key in _handledKeys:
                continue
            if _anyStrKeyExists and isinstance(key, stringtype):
                fullKey = Validator._genFullKey(keyprefix, key)
                handler(self, value, schemeAttrs, fullKey)
            elif not allowUnknownKeys:
                msg = "Unknown key '%s' is in the param %r." % (str(key), keyprefix)
                msg += " Unknown keys aren't allowed here."
                if _anyStrKeyExists:
                    msg += " Only string keys are valid."
                    raise ZenMakeConfTypeError(msg)

                msg += "\nValid values: %r" % sorted(scheme.keys())
                raise ZenMakeConfError(msg)

    def run(self, doAsserts = False):
        """
        Entry point for validation
        """

        try:
            self._process(self._conf, confscheme, '', allowUnknownKeys = True)
        except ZenMakeConfError as ex:
            origMsg = ex.msg
            ex.msg = "Error in the file %r:" % (self._conf['__file__'])
            for line in origMsg.splitlines():
                ex.msg += "\n  %s" % line
            raise ex

        if doAsserts:
            # self checking that scheme was not changed
            assert _oldconfscheme == confscheme
