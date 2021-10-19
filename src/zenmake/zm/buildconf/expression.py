# coding=utf-8
#

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import re

from zm.error import ZenMakeConfError

_RE_REPLACE = re.compile(r"""([\w\d+-_]+)""", re.ASCII)
_RE_CATCH_QUOTES = re.compile(r"""('([^']*)'|"([^"]*)")""", re.ASCII)

class _BuiltIns: # private namespace emulation

    __slots__ = ()

    true = True
    false = False

    startswith = lambda s, prefix: s.startswith(prefix)
    endswith   = lambda s, suffix: s.endswith(suffix)

_CODE_BUILTINS = { k:v for k, v in vars(_BuiltIns).items() if not k.startswith('_') }

class Expression(object):
    """ Class to evalute some python-like expression"""

    __slots__ = ()

    def eval(self, expr, substitutions = None, attrs = None, onError = None):
        """
        Evaluate a python like expression.
        expr - expression
        substitutions - dict of string substitutions in expression
        attrs - dict of actual attributes: functions and variables
        """

        codeGlobals = { '__builtins__': {} }
        codeGlobals.update(_CODE_BUILTINS)
        if attrs is not None:
            codeGlobals.update(attrs)

        code = expr

        if substitutions is not None:

            def replaceVar(match):

                foundName = match.group(1)

                foundVal = substitutions(foundName)
                if foundVal is None:
                    foundVal = foundName

                return foundVal

            # strings in quotes must be ignored
            code = ''
            idx = 0
            for match in _RE_CATCH_QUOTES.finditer(expr):
                start = match.start()
                end = match.end()

                withoutQuotes = expr[idx:start]
                if withoutQuotes:
                    code += _RE_REPLACE.sub(replaceVar, expr[idx:start])
                idx = end

                code += expr[start:end]

            if idx < len(expr):
                code += _RE_REPLACE.sub(replaceVar, expr[idx:])

        try:
            # pylint: disable = eval-used
            # Maybe it's better to make a solution without 'eval'
            # by using a binary tree for example, but current solution is short,
            # just works and has good enough performance.
            # And 'bad' implications of 'eval' don't matter here.
            result = eval(code, codeGlobals)
        except SyntaxError as ex:
            if onError:
                onError(expr, ex)
            else:
                msg = "There is a syntax error in the expression %r." % expr
                raise ZenMakeConfError(msg) from ex

        return result
