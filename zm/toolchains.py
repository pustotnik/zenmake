# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import re
from zm.error import ZenMakeError
from zm.autodict import AutoDict as _AutoDict
from zm.pyutils import stringtype
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
            'fun'    : 'default_compilers'
        },
    },
    'c++' : {
        'env.var'   : 'CXX',
        'env.flagvars' : ('CXXFLAGS', 'CPPFLAGS', 'LDFLAGS'),
        'cfgenv.vars'  : ('CXXFLAGS', 'CPPFLAGS', 'LINKFLAGS', 'LDFLAGS', 'DEFINES'),
        'compiler.list' : {
            'module' : 'waflib.Tools.compiler_cxx',
            'fun'    : 'default_compilers'
        },
    },
}

# private cache
_cache = _AutoDict()

class CompilersInfo(object):
    """
    Class for getting some compiler info for supported compilers
    """

    __slots__ = []

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
    def allVarsToSetCompiler():
        """
        Return combined list of all environment variables to set compiler.
        """

        return [x['env.var'] for x in _langinfo.values()]

    @staticmethod
    def compilers(lang):
        """
        Return compilers set for selected language
        """

        if not lang or lang not in _langinfo:
            raise ZenMakeError("Compiler for '%s' is not supported" % lang)

        compilers = _cache[lang].get('compilers', [])
        if compilers:
            return compilers

        # load chosen module
        getterInfo = _langinfo[lang]['compiler.list']
        module = loadPyModule(getterInfo['module'])
        # and call function
        compilers = getattr(module, getterInfo['fun'])()
        if not isinstance(compilers, stringtype):
            # Code of Waf was changed
            raise NotImplementedError()
        compilers = re.split('[ ,]+', compilers)

        _cache[lang].compilers = compilers
        return compilers

    @staticmethod
    def varToSetCompiler(lang):
        """
        For selected language return environment variable to set compiler.
        """

        if not lang or lang not in _langinfo:
            raise ZenMakeError("Compiler for '%s' is not supported" % lang)
        return _langinfo[lang]['env.var']
