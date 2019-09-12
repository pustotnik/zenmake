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
from zm.utils import loadPyModule

_langinfo = {
    # 'env.var' - environment variable to set compiler
    # 'env.flagvars' - env flag variables that have effect from system environment
    # 'cfgenv.vars' - WAF ConfigSet variables that is used on 'configure' step
    'c' : {
        'env.var'      : 'CC',
        'env.flagvars' : ('CFLAGS', 'CPPFLAGS', 'LDFLAGS'),
        'cfgenv.vars'  : ('CFLAGS', 'CPPFLAGS', 'LINKFLAGS', 'LDFLAGS', 'DEFINES'),
        'compiler.list' : {
            'module' : 'waflib.Tools.compiler_c',
            'var'    : 'c_compiler',
        },
    },
    'c++' : {
        'env.var'   : 'CXX',
        'env.flagvars' : ('CXXFLAGS', 'CPPFLAGS', 'LDFLAGS'),
        'cfgenv.vars'  : ('CXXFLAGS', 'CPPFLAGS', 'LINKFLAGS', 'LDFLAGS', 'DEFINES'),
        'compiler.list' : {
            'module' : 'waflib.Tools.compiler_cxx',
            'var'    : 'cxx_compiler',
        },
    },
}

# private cache
_cache = _AutoDict()

class CompilersInfo(object):
    """
    Class for getting some compiler info for supported compilers
    """

    __slots__ = ()

    @staticmethod
    def allFlagVars():
        """
        For all compilers return list of all env flag variables that have effect
        from system environment.
        """

        _vars = _cache.get('all.env.flag.vars', [])
        if _vars:
            return _vars

        for info in _langinfo.values():
            _vars.extend(info['env.flagvars'])
        _vars = list(set(_vars))
        _cache['all.env.flag.vars'] = _vars
        return _vars

    @staticmethod
    def allCfgEnvVars():
        """
        For all compilers return list of all WAF ConfigSet variables
        that is used on 'configure' step.
        """

        _vars = _cache.get('all.cfg.env.vars', [])
        if _vars:
            return _vars

        for info in _langinfo.values():
            _vars.extend(info['cfgenv.vars'])
        _vars = list(set(_vars))
        _cache['all.cfg.env.vars'] = _vars
        return _vars

    @staticmethod
    def allLangs():
        """
        Return list of all supported programming languages.
        """

        return _langinfo.keys()

    @staticmethod
    def allVarsToSetCompiler():
        """
        Return combined list of all environment variables to set compiler.
        """

        return [ x['env.var'] for x in _langinfo.values() ]

    @staticmethod
    def compilers(lang, platform = PLATFORM):
        """
        Return compilers set for selected language for current platform
        """

        if not lang or lang not in _langinfo:
            raise ZenMakeError("Compiler for language '%s' is not supported" % lang)

        compilers = _cache[platform][lang].get('compilers', [])
        if compilers:
            return compilers

        # load chosen module
        getterInfo = _langinfo[lang]['compiler.list']
        module = loadPyModule(getterInfo['module'])
        # and process var
        table = getattr(module, getterInfo['var'], None)
        if table is None or not isinstance(table, maptype):
            # Code of Waf was changed
            raise NotImplementedError()

        if platform == 'all':
            compilers = list(set(itertools.chain(*table.values())))
        else:
            _platform = platform
            if platform == 'windows':
                _platform = 'win32'
            compilers = table.get(_platform, table['default'])

        _cache[platform][lang].compilers = compilers
        return compilers

    @staticmethod
    def allCompilers(platform = PLATFORM):
        """
        Return list of unique compiler names supported on selected platform
        """

        compilers = _cache[platform].get('all.compilers', [])
        if compilers:
            return compilers

        compilers = [ c for l in _langinfo for c in CompilersInfo.compilers(l, platform) ]
        compilers = list(set(compilers))
        _cache[platform]['all.compilers'] = compilers
        return compilers

    @staticmethod
    def varToSetCompiler(lang):
        """
        For selected language return environment variable to set compiler.
        """

        if not lang or lang not in _langinfo:
            raise ZenMakeError("Compiler for '%s' is not supported" % lang)
        return _langinfo[lang]['env.var']
