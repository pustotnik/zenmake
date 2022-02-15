# coding=utf-8
#

# pylint: disable = missing-docstring, invalid-name

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from zm.pypkg import PkgPath
from zm.utils import loadPyModule
from zm import features
from zm.features import MODULE_NAME_PREFIX

def _getInitModuleNames():

    pkgPath = PkgPath(os.path.dirname(os.path.abspath(features.__file__)))
    fnames = pkgPath.files()
    names = [ x for x in fnames if x.endswith('_init.py') ]
    names = [ x[:-3] for x in names]
    return names

def testInitModules():

    names = _getInitModuleNames()

    targetMap = {}
    extensionsMap = {}
    scheme = {}

    for name in names:
        module = loadPyModule(MODULE_NAME_PREFIX + name)

        spec = getattr(module, 'TASK_FEATURES_SETUP', {})
        for feature, params in spec.items():
            if not params:
                continue

            targetKinds = params.get('target-kinds', [])
            for tkind in targetKinds:
                targetFeature = feature + tkind
                assert targetFeature not in targetMap
                targetMap[targetFeature] = feature

            extensions = params.get('file-extensions', [])
            for ext in extensions:
                assert ext not in extensionsMap
                extensionsMap[ext] = feature

        spec = getattr(module, 'CONF_TASKSCHEME_SPEC', {})
        spec = spec.get('base', {})
        for param in spec:
            assert param not in scheme
        scheme.update(spec)

def testDetectTaskFeatures():
    taskParams = {}
    assert features.detectTaskFeatures(taskParams) == []

    taskParams = { 'features' : '' }
    assert features.detectTaskFeatures(taskParams) == []

    for ftype in ('stlib', 'shlib', 'program'):
        for lang in ('c', 'cxx'):
            fulltype = '%s%s' % (lang, ftype)

            taskParams = { 'features' : fulltype }
            assert sorted(features.detectTaskFeatures(taskParams)) == sorted([
                lang, fulltype
            ])

            taskParams = { 'features' : [lang, fulltype] }
            assert sorted(features.detectTaskFeatures(taskParams)) == sorted([
                lang, fulltype
            ])
