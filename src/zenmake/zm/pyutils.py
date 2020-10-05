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

PY_MAJOR_VER = sys.version_info[0]
PY2 = PY_MAJOR_VER == 2
PY3 = PY_MAJOR_VER >= 3

#pylint: disable=wrong-import-position,missing-docstring
#pylint: disable=invalid-name,undefined-variable,unused-import

if PY3:
    stringtype = str # pragma: no cover
    texttype = str # pragma: no cover
    binarytype = bytes # pragma: no cover
    _t = str # pragma: no cover

    def _unicode(s):
        return s

    def _encode(s):
        return s

else:
    stringtype = basestring # pragma: no cover
    texttype = unicode # pragma: no cover
    binarytype = str # pragma: no cover
    _t = unicode # pragma: no cover

    def _unicode(s):
        return unicode(s, 'utf-8', 'replace')

    def _encode(s):
        return s.encode('utf-8', 'replace')

from collections.abc import Mapping, MutableMapping
maptype = Mapping
