# coding=utf-8
#

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

def _genSchemeWithFilter(confscheme, fromTaskParam, sugarParam):

    byfilterDictVars = confscheme['byfilter']['dict-vars']
    origSchemeFunc = confscheme['tasks']['vars'][fromTaskParam]
    topScheme = origSchemeFunc(None, None)
    itemsOrigSchemeFunc = topScheme['dict-vars']

    def genParamsScheme(confnode, fullkey):

        scheme = itemsOrigSchemeFunc(confnode, fullkey)
        scheme.update({
            'for'     : byfilterDictVars['for'],
            'not-for' : byfilterDictVars['not-for'],
        })

        return scheme

    scheme = topScheme.copy()
    scheme['dict-vars'] = genParamsScheme
    confscheme[sugarParam] = scheme

def _genConfigureScheme(confscheme):
    _genSchemeWithFilter(confscheme, 'configure', 'configure')

def _genInstallScheme(confscheme):
    _genSchemeWithFilter(confscheme, 'install-files', 'install')

def _applyAttrByFilter(buildconf, attrName, toSet):

    attr = getattr(buildconf, attrName, [])

    byfilter = []
    for item in attr:
        _for = item.pop('for', 'all')
        _notfor = item.pop('not-for', {})

        byfilter.append({
            'for' : _for, 'not-for' : _notfor,
            'set' : toSet(item),
        })

    # insert into beginning
    buildconf.byfilter[0:0] = byfilter

    try:
        delattr(buildconf, attrName)
    except AttributeError:
        pass

def _applyConfigure(buildconf):
    _applyAttrByFilter(buildconf, 'configure', lambda x: { 'configure': [x] } )

def _applyInstall(buildconf):
    _applyAttrByFilter(buildconf, 'install', lambda x: { 'install-files': [x] } )

def genSugarSchemes(confscheme):
    """
    Generate validation schemes for syntactic sugar
    """

    _genConfigureScheme(confscheme)
    _genInstallScheme(confscheme)

def applySyntacticSugar(buildconf):
    """
    Convert syntactic sugar constructions in buildconf
    """

    _applyConfigure(buildconf)
    _applyInstall(buildconf)
