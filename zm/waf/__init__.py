# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from zm.utils import loadPyModule

_cache = {}

def allAddOnNames():
    """ Return list of all existent add-ons here """

    if _cache:
        return _cache.keys()

    names = []
    for _, _, fnames in os.walk(os.path.dirname(os.path.abspath(__file__))):
        names = [ x for x in fnames if x.startswith('addon_') and x.endswith('.py') ]
        names = [ x[6:-3] for x in names ]
        break

    for name in names:
        _cache[name] = None
    return names

def loadAllAddOns():
    """ Load all existent add-ons here """

    addons = []
    addonNames = allAddOnNames()
    for name in addonNames:
        addons.append(getAddOn(name))
    return addons

def getAddOn(name):
    """ Get/Load add-on by name """
    names = allAddOnNames()
    if name not in names:
        raise NotImplementedError("Add-on %r is not implemented" % name)

    addon = _cache.get(name)
    if not addon:
        moduleName = 'zm.waf.addon_%s' % name
        addon = loadPyModule(moduleName, withImport = True)
        setup = getattr(addon, 'setup', None)
        if setup:
            setup()
        _cache[name] = addon

    return addon
