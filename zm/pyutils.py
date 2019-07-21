# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some python2/3 compatible stuffs. I don't use six because I don't want
 to have extra dependencies. Also here can be some extra stuffs based on
 python built-in ones.
"""

import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] >= 3

#pylint: disable=wrong-import-position
#pylint: disable=invalid-name,undefined-variable,unused-import

if PY3:
    stringtype = str # pragma: no cover
else:
    stringtype = basestring # pragma: no cover

try:
    from collections.abc import Mapping as maptype
except ImportError:
    from collections import Mapping as maptype

try:
    from collections.abc import Sequence as seqtype
except ImportError:
    from collections import Sequence as seqtype
