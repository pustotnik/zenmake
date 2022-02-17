# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import itertools

from zm.error import ZenMakeError
from zm.autodict import AutoDict as _AutoDict
from zm.pyutils import maptype
from zm.constants import PLATFORM

# Table with language toolchains
_langTable = {}

# private cache
_cache = _AutoDict()

def reset():
    """
    Reset all cached values
    """

    _cache.clear()

def regToolchains(lang, table):
    """
    Register table of toolchains for selected lang.
    """

    _langTable[lang] = table

def knownLangs():
    """
    Return all langs of registered toolchains.
    """

    return _langTable.keys()

def getNames(lang, platform = PLATFORM, withAuto = False):
    """
    Return toolchains tuple for selected language for current platform
    """

    if not lang or lang not in _langTable:
        raise ZenMakeError("Toolchain for feature '%s' is not supported" % lang)

    cacheKey = 'toolchains-withauto' if withAuto else 'toolchains'
    cache = _cache[platform][lang]

    toolchains = cache.get(cacheKey)
    if toolchains:
        return toolchains

    table = _langTable[lang]
    if table is None or not isinstance(table, maptype):
        # Code of Waf was changed
        raise NotImplementedError()

    if platform == 'all':
        toolchains = tuple(set(itertools.chain(*table.values())))
    else:
        _platform = platform
        if platform == 'windows':
            _platform = 'win32'
        toolchains = tuple(table.get(_platform, table['default']))

    cache['toolchains'] = toolchains
    cache['toolchains-withauto'] = toolchains + ('auto-' + lang.replace('xx', '++'),)
    return cache.get(cacheKey)

def getAllNames(platform = PLATFORM, withAuto = False):
    """
    Return tuple of unique names of toolchains supported and loaded at the moment
    """

    cacheKey = 'all-toolchains-withauto' if withAuto else 'all-toolchains'
    cache = _cache[platform]

    toolchains = cache.get(cacheKey)
    if toolchains:
        return toolchains

    toolchains = [ t for l in _langTable for t in getNames(l, platform) ]
    toolchains = tuple(set(toolchains))
    cache['all-toolchains'] = toolchains
    autoNames = ['auto-' + lang.replace('xx', '++') for lang in _langTable ]
    cache['all-toolchains-withauto'] = toolchains + tuple(autoNames)

    return cache.get(cacheKey)

def getLangs(toolchain):
    """
    Get toolchain supported languages.
    """

    if not toolchain:
        return []

    toolToLang = _cache.get('toolchain-to-lang')

    if not toolToLang:
        toolToLang = {}
        for lang in _langTable:
            toolchains = getNames(lang, withAuto = True)
            for tool in toolchains:
                toolList = toolToLang.setdefault(tool, [])
                toolList.append(lang)
        _cache['toolchain-to-lang'] = toolToLang

    return toolToLang.get(toolchain)
