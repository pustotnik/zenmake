# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import re
from waflib.Errors import WafError
from autodict import AutoDict
import utils

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
_cache = AutoDict()

class CompilersInfo(object):
    
    @staticmethod
    def allFlagVars():
        vars = _cache.get('all.env.flag.vars', [])
        if vars:
            return vars

        for lang, info in _langinfo.items():
            vars.extend(info['env.flagvars'])
        vars = list(set(vars))
        _cache['all.env.flag.vars'] = vars
        return vars

    @staticmethod
    def allCfgEnvVars():
        vars = _cache.get('all.cfg.env.vars', [])
        if vars:
            return vars

        for lang, info in _langinfo.items():
            vars.extend(info['cfgenv.vars'])
        vars = list(set(vars))
        _cache['all.cfg.env.vars'] = vars
        return vars
    
    @staticmethod
    def allVarsToSetCompiler():
        return [x['env.var'] for x in _langinfo.values()]

    @staticmethod
    def compilers(lang):
        if not lang or lang not in _langinfo:
            raise WafError("Compiler for '%s' is not supported" % lang)

        compilers = _cache[lang].get('compilers', [])
        if compilers:
            return compilers

        # load chosen module
        getterInfo = _langinfo[lang]['compiler.list']
        module = utils.loadPyModule(getterInfo['module'])
        # and call function
        compilers = getattr(module, getterInfo['fun'])()
        if isinstance(compilers, utils.stringtypes):
            compilers = re.split('[ ,]+', compilers)
        
        _cache[lang].compilers = compilers
        return compilers
    
    @staticmethod
    def varToSetCompiler(lang):
        if not lang or lang not in _langinfo:
            raise WafError("Compiler for '%s' is not supported" % lang)
        return _langinfo[lang]['env.var']
