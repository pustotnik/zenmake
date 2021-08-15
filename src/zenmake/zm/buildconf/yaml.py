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
import re

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

_VALID_SUBST_MODES = ('yaml-tag', 'yaml-tag-noenv', 'preparse', 'preparse-noenv')

# pyyaml uses re.match to detect tag so it's necessary to use .*
_RE_DETECT_SUBST_TAG = re.compile(r".*?\$(\w+|\{\{\s*\w+\s*\}\}).*?", re.ASCII)
_RE_SUBST = re.compile(r"\$(\w+)|\$\{\{\s*(\w+)\s*\}\}", re.ASCII)

def _substitute(data, regexp, svars, preparseMode = False):

    def replaceVar(match):
        foundName = match.group(1,2)
        foundName = [x for x in foundName if x][0]
        foundVal = svars.get(foundName)

        if foundVal is None:
            # restore original value
            foundVal = match.group(0)
        elif preparseMode and '\n' in foundVal:
            foundVal = '"' + foundVal.replace('\n', "\\n") + '"'
        return foundVal

    return regexp.sub(replaceVar, data)

class SubstYamlLoader(YamlLoader):
    """
    YamlLoader class with substitutions
    """

    # pylint: disable = too-many-ancestors

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.substVars = None

def _constructSubst(loader, node):

    value = loader.construct_scalar(node)
    substVars = loader.substVars
    if not substVars:
        return value

    return _substitute(value, _RE_SUBST, substVars)

SubstYamlLoader.add_implicit_resolver('!subst', _RE_DETECT_SUBST_TAG, first = None)
SubstYamlLoader.add_constructor('!subst', _constructSubst)

class StringIO(io.StringIO):
    """
    Customized StringIO
    """

    def __init__(self, data, name = '<file>'):
        super().__init__(data)
        # it's used in pyyaml for error reports
        self.name = name

def _findConfDataPos(stream):

    dataPos = 0
    stopIdx = 2
    nextDocIdx = 0

    readCharsCount = 0
    for line in stream:
        readCharsCount += len(line)

        #if line.startswith('---') and len(line) > 3 and line[3].isspace():
        if line.startswith('---') and len(line) > 3 \
                and line[3] in '\0 \t\r\n\x85\u2028\u2029':
            nextDocIdx += 1
            if nextDocIdx == 2:
                dataPos = readCharsCount
            continue
        if line == '...\n':
            break
        if nextDocIdx >= stopIdx:
            break
        if line.startswith('%'):
            continue
        if nextDocIdx == 0:  # no initial '---'
            _line = line.lstrip()
            if not _line or _line.startswith('#'):
                continue
            nextDocIdx = 1

    stream.seek(0)
    return dataPos if (nextDocIdx > 1) else 0

def _validateSubstMode(substmode, filepath):
    if not isinstance(substmode, stringtype):
        msg = "File %r:\n" % filepath
        msg += "  The 'substmode' parameter must be a string"
        raise ZenMakeConfError(msg)

    if substmode not in _VALID_SUBST_MODES:
        msg = "File %r:\n" % filepath
        msg += "  The value %r for the 'substmode' is invalid" % substmode
        msg += ", must be one of: %s" % str(_VALID_SUBST_MODES)[1:-1]
        raise ZenMakeConfError(msg)

def load(filepath):
    """
    Load YAML buildconf
    """

    buildconf = types.ModuleType('buildconf')
    buildconf.__file__ = os.path.abspath(filepath)
    data = {}

    osenv = os.environ.copy()
    substVars = {}
    substmode = 'yaml-tag'

    # buildconf file should not be very big so it's loaded completely in memory
    # to optimize its data rereading later
    with io.open(filepath, 'rt', encoding = 'utf-8') as fstream:
        stream = StringIO(fstream.read(), fstream.name)

    header = {}
    dataPos = _findConfDataPos(stream)

    try:

        if dataPos > 0:
            # read header and shift file position to main config data
            loader = YamlLoader(stream.read(dataPos))
            # get header as a python object
            header = loader.get_data()
            loader = None # mark it as invalid to use and ready to free

            substmode = header.pop('substmode', substmode)
            _validateSubstMode(substmode, filepath)

        substVars.update(header)
        if not substmode.endswith('-noenv'):
            substVars.update(osenv)

        # We should allow pyyaml to read stream from the beginning to have
        # correct number of line and column in error messages
        stream.seek(0)

        if substmode.startswith('yaml-tag'):
            loader = SubstYamlLoader(stream)
            loader.substVars = substVars
        else: # preparse/preparse-noenv
            if substVars:
                yamlData = _substitute(stream.read(), _RE_SUBST, substVars, True)
                stream = StringIO(yamlData, stream.name)
            loader = YamlLoader(stream)

        if dataPos > 0:
            # skip first document
            loader.get_data()

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
