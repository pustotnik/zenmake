# coding=utf-8
#

"""
 Copyright (c) 2022, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from collections.abc import MutableMapping

# Variable to control turning on/off of recording of used variables
doMonitoring = False

_monitored = set()

class MonitoredEnviron(MutableMapping):
    """
    Class to try to monitor all used environment variables.
    The way used is based on the assumption that usually the methods 'get' or
    '__contain__' are used. But it is not perfect way because there is no way
    to catch all used environment variables due to implementation of
    os.environ as dict-like object. For example an iteration through all items
    can be used while only some of these items are actually used or even
    none of them and we cannot check it.
    """

    __slots__ = ('_data', )

    def __init__(self, data):
        self._data = data

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __setitem__(self, key, value):
        self._data.__setitem__(key, value)

    def __delitem__(self, key):
        self._data.__delitem__(key)

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return self._data.__repr__()

    def __copy__(self):
        return self._data.__copy__()

    def copy(self):
        ''' just proxy to 'copy' '''
        return self._data.copy()

    def setdefault(self, key, default = None):
        return self._data.setdefault(key, default)

    def get(self, key, default = None):
        if doMonitoring:
            _monitored.add(key)
        return self._data.get(key, default)

    def __contains__(self, key):
        if doMonitoring:
            _monitored.add(key)
        return self._data.__contains__(key)

def assignMonitoringTo(owner, objName):
    """ Assign monitoring to an object """

    obj = MonitoredEnviron(getattr(owner, objName))
    setattr(owner, objName, obj)

def monitoredVars():
    """ Get set of recorded monitored env vars """
    return _monitored

def addMonitoredVar(varName):
    """ Add name to the set of recorded monitored env vars """
    _monitored.add(varName)
