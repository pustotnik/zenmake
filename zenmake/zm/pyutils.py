# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some python2/3 compatible stuffs. I don't use 'six' because I don't want
 to have extra dependencies. Also here can be some extra stuffs based on
 python only built-in ones.
"""

import sys
import operator

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3

#pylint: disable=wrong-import-position,missing-docstring
#pylint: disable=invalid-name,undefined-variable,unused-import

if PY3:
    stringtype = str # pragma: no cover
    texttype = str # pragma: no cover
    binarytype = bytes # pragma: no cover
else:
    stringtype = basestring # pragma: no cover
    texttype = unicode # pragma: no cover
    binarytype = str # pragma: no cover

try:
    from collections.abc import Mapping as maptype
except ImportError:
    from collections import Mapping as maptype

try:
    from collections.abc import Sequence as seqtype
except ImportError:
    from collections import Sequence as seqtype

if PY3:
    def iterkeys(d):
        return iter(d.keys())

    def itervalues(d):
        return iter(d.values())

    def iteritems(d):
        return iter(d.items())

    viewkeys   = operator.methodcaller('keys')
    viewvalues = operator.methodcaller('values')
    viewitems  = operator.methodcaller('items')

    def listvalues(d):
        return list(d.values())
    def listitems(d):
        return list(d.items())

else:
    iterkeys   = operator.methodcaller('iterkeys')
    itervalues = operator.methodcaller('itervalues')
    iteritems  = operator.methodcaller('iteritems')
    viewkeys   = operator.methodcaller('viewkeys')
    viewvalues = operator.methodcaller('viewvalues')
    viewitems  = operator.methodcaller('viewitems')
    listvalues = operator.methodcaller('values')
    listitems  = operator.methodcaller('items')
