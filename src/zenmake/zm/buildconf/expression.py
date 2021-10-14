# coding=utf-8
#

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import re

from zm.error import ZenMakeConfError

_RE_REPLACE = re.compile(r"""([^\s"'\(\)]+)""", re.ASCII)

class Expression(object):
    """ Class to evalute some python-like expression"""

    __slots__ = ('_operators',)

    def __init__(self, allowedOperators):

        self._operators = allowedOperators

    def eval(self, expr, resolver, bconfPath = None):
        """
        Evaluate 'expr'
        """

        codeLocals = {}

        def replaceVar(match):

            foundName = match.group(1)

            if foundName in self._operators:
                return foundName

            foundVal = resolver(foundName)

            if foundVal:
                if callable(foundVal):
                    funcName = foundVal.__name__
                    codeLocals[funcName] = foundVal
                    foundVal = "%s(%r)" % (funcName, foundName)
            else:
                foundVal = foundName

            return foundVal

        code = _RE_REPLACE.sub(replaceVar, expr)

        try:
            # pylint: disable = eval-used
            # Maybe it's better to make a solution without 'eval'
            # by using a binary tree for example, but current solution is short,
            # just works and has good enough performance.
            # And 'bad' implications of 'eval' don't matter here.
            result = eval(code, { '__builtins__': {} }, codeLocals)
        except SyntaxError as ex:
            msg = "There is syntax error in the expression %r." % expr
            raise ZenMakeConfError(msg, confpath = bconfPath) from ex

        return result
