# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys

from waflib import Utils
from waflib.TaskGen import after_method, feature
from waflib.Tools import ccroot as wafccroot # don't remove

from zm.utils import asmethod, toList, toListSimple, uniqueListWithOrder
from zm.features import TASK_TARGET_FEATURES_TO_LANG
from zm.waf.assist import makeTargetRealName

# waflib.Tools.ccroot must be always imported
assert 'waflib.Tools.ccroot' in sys.modules

USELIB_VARS = wafccroot.USELIB_VARS

@asmethod(wafccroot.link_task, 'add_target')
def _addTargetToLinkTask(self, target):

    if isinstance(target, str):
        tgen = self.generator
        baseNode = tgen.path

        # This code was copied from Waf but it's not found where it's used.
        # So this code is disabled while nobody reports a problem with it.
        #if target.startswith('#'):
        #    # for those who like flat structures
        #    target = target[1:]
        #    baseNode = tgen.bld.bldnode

        zmTaskParams = getattr(tgen, 'zm-task-params', {})
        # small optimization: don't calculate target if it exists already
        _target = zmTaskParams.get('$real.target')
        if not _target:
            targetFeature = self.__class__.__name__
            pattern = self.env[targetFeature + '_PATTERN']
            lang = TASK_TARGET_FEATURES_TO_LANG[targetFeature]
            targetKind = targetFeature[len(lang):]
            _target = makeTargetRealName(target, targetKind, pattern,
                                         self.env, getattr(tgen, 'vnum', None))
        target = baseNode.find_or_declare(_target)

    self.set_outputs(target)

@feature('c', 'cxx', 'd', 'fc', 'javac', 'cs', 'uselib', 'asm')
@after_method('process_use')
def propagate_uselib_vars(self):
    """
    Alternative version of propagate_uselib_vars from waflib.Tools.ccroot
    The main reason is to change order of flag vars
    """

    # pylint: disable = invalid-name

    # RIGHT ORDERS
    # by default (waf order): env + tgen attr + uselib_feature
    # flags: uselib_feature (defaults) + tgen attr + env (custom)
    # (st)lib: env (from 'use') + tgen attr (deps + custom + system) + uselib_feature (?)
    # (st)libpath: env (from 'use') + tgen attr (custom + system) + uselib_feature (defaults?)

    useLibVars = self.get_uselib_vars()
    env = self.env

    useLibFeatures = self.features + toListSimple(getattr(self, 'uselib', []))
    for var in useLibVars:
        param = var.lower()

        tgenVals = getattr(self, param, [])
        if tgenVals:
            tgenVals = toList(tgenVals)

        featureVals = []
        for _feature in useLibFeatures:
            val = env['%s_%s' % (var, _feature)]
            if val:
                featureVals += val

        if tgenVals or featureVals:

            if param.endswith('flags'):
                # User flags are set in env, so env must be last in order
                vals = featureVals + tgenVals + env[var]
            else:
                vals = env[var] + tgenVals + featureVals

            # remove duplicates: keep only last unique values in the list
            vals = uniqueListWithOrder(reversed(vals))
            vals.reverse()
            env[var] = vals

#TODO: remove it when this patch appears in the Waf
# See https://gitlab.com/ita1024/waf/issues/2272
if Utils.is_win32:
    @feature('c', 'cxx', 'd', 'asm', 'fc', 'includes')
    @after_method('propagate_uselib_vars', 'process_source')
    def apply_incpaths(self):
        # pylint: disable = invalid-name, missing-docstring
        lst = self.to_incnodes(toList(getattr(self, 'includes', [])) + self.env.INCLUDES)
        self.includes_nodes = lst
        cwd = self.get_cwd()
        self.env.INCPATHS = [x.path_from(cwd) if x.is_child_of(self.bld.srcnode) \
                             else x.abspath() for x in lst]
