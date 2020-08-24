# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import TaskGen as WafTaskGen
from zm.pyutils import viewitems
from zm.utils import asmethod
from zm import error

@asmethod(WafTaskGen.task_gen, 'get_hook')
def _tgenGetHook(self, node):

    name = node.name
    for k in self.mappings:
        try:
            if name.endswith(k):
                return self.mappings[k]
        except TypeError:
            # regexps objects
            if k.match(name):
                return self.mappings[k]

    # Make appropriate error message for ZenMake, not for Waf

    from zm.features import FILE_EXTENSIONS_TO_LANG

    supportedExts = []
    for ext, lang in viewitems(FILE_EXTENSIONS_TO_LANG):
        if lang in self.features:
            supportedExts.append(ext)
    supportedExts = ', '.join(supportedExts)

    msg = "File %r has unkwnown/unsupported extension." % node
    msg += "\nSupported file extensions for task %r are: %s" % (self.name, supportedExts)
    if error.verbose > 0:
        mapExts = ', '.join(self.mappings.keys())
        msg += "\nRegistered file extensions for task %r are: %s" % (self.name, mapExts)
    raise error.ZenMakeError(msg)
