# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from collections import defaultdict, deque

from waflib import TaskGen as WafTaskGen
from zm.pyutils import asmethod
from zm.utils import toList
from zm import error

_taskGen = WafTaskGen.task_gen
_taskGen.pmappings = defaultdict(deque)
_taskGen.fmappings = defaultdict(dict)

@asmethod(_taskGen, '__init__', wrap = True, callOrigFirst = True)
def _taskGenInit(self, *args, **kwargs):
    # pylint: disable = unused-argument

    self.featureMappings = None

def extension(*exts):
    """
    Alternative version of the @extension decorator
    """

    def decorator(func):
        setattr(_taskGen, func.__name__, func)
        for ext in exts:
            old = _taskGen.mappings.get(ext)
            if old is not None:
                _taskGen.pmappings[ext].append(old)
            _taskGen.mappings[ext] = func
        return func
    return decorator

extension.__doc__ = WafTaskGen.extension.__doc__
WafTaskGen.extension = extension

# re-register WafTaskGen.add_pcfile after altering of the @extension decorator
assert len(_taskGen.mappings) <= 1
_taskGen.mappings.clear()
extension('.pc.in')(WafTaskGen.add_pcfile)

def isolatedExt(exts, feature):
    """
    Decorator to declare file extension handler to a particular feature
    """

    def decorator(func):
        for ext in exts:
            old = _taskGen.pmappings[ext]
            if old:
                _taskGen.mappings[ext] = old.pop()
            else:
                del _taskGen.mappings[ext]
            _taskGen.fmappings[feature][ext] = func
        return func

    return decorator

def isolateExtHandler(handler, exts, feature):
    """
    Isolate existing file extension handler to a particular feature
    """

    isolatedExt(exts, feature)(handler)

def _getExtensions(name):

    if name[0] == '.':
        name = name[1:]

    exts = []
    suffixes = name.split('.')[1:]
    while suffixes:
        exts.append('.' + '.'.join(suffixes))
        suffixes = suffixes[1:]

    return exts

@asmethod(_taskGen, 'get_hook')
def _tgenGetHook(self, node):

    name = node.name
    exts = _getExtensions(name)

    featureMappings = self.featureMappings
    if featureMappings is None:
        featureMappings = {}
        features = [x for x in self.features if x in _taskGen.fmappings]
        if features:
            assert len(features) == 1 # error?
            featureMappings = _taskGen.fmappings[features[0]]

        self.featureMappings = featureMappings

    for ext in exts:
        hook = featureMappings.get(ext, self.mappings.get(ext))
        if hook is not None:
            return hook

    # Make appropriate error message for ZenMake, not for Waf

    from zm.features import FILE_EXTENSIONS_TO_LANG

    supportedExts = []
    for ext, lang in FILE_EXTENSIONS_TO_LANG.items():
        if lang in self.features:
            supportedExts.append(ext)
    supportedExts = ', '.join(supportedExts)

    msg = "File %r has unknown/unsupported extension." % node
    msg += "\nSupported file extensions for task %r are: %s" % (self.name, supportedExts)
    if error.verbose > 0:
        mapExts = ', '.join(self.mappings.keys())
        mapExts += ', '.join(featureMappings.keys())
        msg += "\nRegistered file extensions for task %r are: %s" % (self.name, mapExts)
    raise error.ZenMakeError(msg)

@WafTaskGen.feature('*')
@WafTaskGen.before('process_rule', 'process_source', 'process_subst',
                   'process_marshal', 'process_mocs')
def makesource(tgen):
    """
    Waf doesn't expect a generator in 'source' and this causes an error in some cases.
    This function makes generator from ZenMake to generate all values in a list.
    """

    source = getattr(tgen, 'source', None)
    if not source:
        return

    # The function 'toList' ignores a generator but it's needed because of
    # calls from config actions where it can be a string
    tgen.source = list(toList(source))

    zmTaskParams = getattr(tgen, 'zm-task-params', {})
    if zmTaskParams:
        # sync ZenMake task params with the new value, just in case
        zmTaskParams['source'] = tgen.source
