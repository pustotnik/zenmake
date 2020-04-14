# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import Task as WafTask, Node as WafNode, Errors as waferror
from zm.constants import TASK_TARGET_KINDS, SYSTEM_LIB_PATHS
from zm.utils import asmethod
from zm.features import TASK_TARGET_FEATURES_TO_LANG

APPLY_MONITLIBS_TASKTYPES = tuple(TASK_TARGET_KINDS)

def _getPathNode(bld, path):
    if not isinstance(path, WafNode.Node):
        return bld.root.find_node(path)
    return path

@asmethod(WafTask.Task, 'sig_explicit_deps', wrap = True, callOrigFirst = True)
def _signatureExplicitDeps(self):

    cname = self.__class__.__name__
    if not cname.endswith(APPLY_MONITLIBS_TASKTYPES):
        return

    taskgen = self.generator
    bld = taskgen.bld
    updateHash = self.m.update

    for libsparam, targetkind in (('lib', 'shlib'), ('stlib', 'stlib')):
        libs = getattr(taskgen, 'monit%ss' % libsparam, None)
        if libs is None:
            continue

        libpaths = getattr(taskgen, libsparam + 'path', [])
        libpaths += SYSTEM_LIB_PATHS

        lang = TASK_TARGET_FEATURES_TO_LANG[cname]
        pattern = self.env[lang + targetkind + '_PATTERN']
        libs = [ pattern % lib for lib in libs]

        for path in libpaths:
            path = _getPathNode(bld, path)
            if not path:
                continue

            notfound = []
            for lib in libs:
                libnode = path.find_node(lib)
                if libnode:
                    updateHash(libnode.get_bld_sig())
                else:
                    notfound.append(lib)
            libs = notfound

        if libs:
            if len(libs) > 1:
                msg = 'could not find libraries %s' % str(libs)[1:-1]
            else:
                msg = 'could not find library %r' % libs[0]
            msg += '\nsearch paths: %s' % str(libpaths)[1:-1]
            raise waferror.WafError(msg)
