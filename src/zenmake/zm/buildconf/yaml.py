# coding=utf-8
#

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

__all__ = [
    'load',
]

import os
import io
import types

from zm.error import ZenMakeConfError
from zm.pyutils import maptype, stringtype

_INTERNAL_PYYAML = True
try:
    import yaml as pyyaml
    _INTERNAL_PYYAML = False
except ImportError:
    from auxiliary.pyyaml import yaml as pyyaml
    YamlLoader = pyyaml.SafeLoader

if not _INTERNAL_PYYAML:
    try:
        YamlLoader = pyyaml.CSafeLoader
    except AttributeError:
        YamlLoader = pyyaml.SafeLoader

class StringIO(io.StringIO):
    """
    Customized StringIO
    """

    def __init__(self, data, name = '<file>'):
        super().__init__(data)
        # it's used in pyyaml for error reports
        self.name = name

def load(filepath):
    """
    Load YAML buildconf
    """

    buildconf = types.ModuleType('buildconf')
    buildconf.__file__ = os.path.abspath(filepath)
    data = {}

    # buildconf file should not be very big so it's loaded completely in memory
    # to optimize its data rereading later
    with io.open(filepath, 'rt', encoding = 'utf-8') as fstream:
        stream = StringIO(fstream.read(), fstream.name)

    try:

        loader = YamlLoader(stream)

        # load main config data as a python map
        data = loader.get_data()

    except pyyaml.YAMLError as ex:
        raise ZenMakeConfError(ex = ex) from ex

    if data is None:
        raise ZenMakeConfError("File %r has no config data" % filepath)

    if not isinstance(data, maptype):
        raise ZenMakeConfError("File %r has invalid structure" % filepath)

    for k, v in data.items():
        if not isinstance(k, stringtype):
            msg = "File %r:\n" % filepath
            msg += "  The variable %r is not string" % k
            raise ZenMakeConfError(msg)
        setattr(buildconf, k, v)

    return buildconf
