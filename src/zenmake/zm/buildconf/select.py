# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from zm.constants import PLATFORM, KNOWN_PLATFORMS, HOST_OS, DISTRO_INFO, CPU_ARCH
from zm.utils import toList
from zm.error import ZenMakeLogicError, ZenMakeConfError
from zm.buildconf.scheme import KNOWN_CONDITION_PARAM_NAMES
from zm.buildconf.expression import Expression
from zm.features import areFeaturesLoaded
from zm.toolchains import getAllNames as getAllToolchainNames

_SYS_STATES = (
    ('platform', PLATFORM),
    ('host-os', HOST_OS),
    ('distro', DISTRO_INFO.get('ID', '')),
    ('cpu-arch', CPU_ARCH),
)

_exprHandler = Expression()

# module local cache
_local = {}

def _getReadyConditions(bconf):

    bconfId = id(bconf)
    _local.setdefault('ready-conditions', {})
    conditions = _local['ready-conditions'].get(bconfId)
    if conditions is not None:
        return conditions

    if not areFeaturesLoaded():
        msg = "Programming error: task features have not been loaded yet"
        raise ZenMakeLogicError(msg)

    conditions = _local.get('common-ready-conditions')
    if conditions is None:
        conditions = {}
        # platform conditions
        for platform in KNOWN_PLATFORMS:
            conditions[platform] = { 'platform' : (platform, ) }
        conditions['macos'] = { 'host-os' : ('macos', ) }
        # toolchain conditions
        for toolchain in getAllToolchainNames(platform = 'all'):
            assert toolchain not in conditions
            conditions[toolchain] = { 'toolchain' : (toolchain, ) }
        _local['common-ready-conditions'] = conditions

    # don't change common conditions
    conditions = conditions.copy()

    buildtypes = bconf.supportedBuildTypes
    for buildtype in buildtypes:
        if buildtype not in conditions:
            conditions[buildtype] = { 'buildtype' : (buildtype, ) }

    _local['ready-conditions'][bconfId] = conditions
    return conditions

def _tryToSelect(bconf, condName, taskParams, paramName):
    # pylint: disable = too-many-return-statements

    condition = bconf.conditions.get(condName,
                                _getReadyConditions(bconf).get(condName))
    if condition is None:
        msg = "Task %r: " % taskParams['name']
        msg += "there is no condition %r in buildconf.conditions" % condName
        raise ZenMakeConfError(msg, confpath = bconf.path)

    # check we didn't forget any param
    assert frozenset(condition.keys()) <= KNOWN_CONDITION_PARAM_NAMES

    # check system states
    for name, val in _SYS_STATES:
        filterVals = condition.get(name)
        if filterVals is not None and val not in filterVals:
            return False

    # check task
    filterVals = condition.get('task')
    if filterVals is not None and taskParams['name'] not in filterVals:
        return False

    # check buildtype
    buildtype = bconf.selectedBuildType
    filterVals = condition.get('buildtype')
    if filterVals is not None and buildtype not in filterVals:
        return False

    # check toolchain
    filterVals = condition.get('toolchain')
    if filterVals is not None:
        if paramName == 'toolchain':
            msg = "Task %r: " % taskParams['name']
            msg += "Condition %r in buildconf.conditions" % condName
            msg += " cannot be used to select toolchain because it"
            msg += " contains the 'toolchain' parameter."
            raise ZenMakeConfError(msg, confpath = bconf.path)

        filterVals = set(filterVals)
        taskToolchains = toList(taskParams.get('toolchain', []))
        if not filterVals.issubset(taskToolchains):
            return False

    # check system env vars
    filterVals = condition.get('env', {})
    for var, val in filterVals.items():
        if os.environ.get(var) != val:
            return False

    return True

def clearLocalCache():
    """ Clear module local cache. It's mostly for tests """
    _local.clear()

def handleOneTaskParamSelect(bconf, taskParams, paramName):
    """
    Handle one <param name>.select
    """

    selectName = '%s.select' % paramName

    selectParam = taskParams.get(selectName)
    if selectParam is None:
        return

    defaultValue = selectParam.get('default', taskParams.get(paramName))
    detectedValue = None

    def handleCond(name):
        return _tryToSelect(bconf, name, taskParams, paramName)

    exprAttrs = { 'handleCond': handleCond }

    def exprSubsts(keyword):
        if keyword in ('and', 'or', 'not'):
            return keyword

        return '%s(%r)' % ('handleCond', keyword)

    def onExprError(expr, ex):
        msg = "There is syntax error in the expression: %r." % expr
        raise ZenMakeConfError(msg, confpath = bconf.path) from ex

    for label, param in selectParam.items():
        if label == 'default':
            continue

        # try one record of conditions
        if _exprHandler.eval(label, exprSubsts, exprAttrs, onExprError):
            # found
            detectedValue = param

        if detectedValue is not None:
            # already found, stop loop
            break

    if detectedValue is None:
        detectedValue = defaultValue

    if detectedValue is None:
        taskParams.pop(paramName, None)
    else:
        taskParams[paramName] = detectedValue

    # remove *.select param
    taskParams.pop(selectName, None)

def handleTaskParamSelects(bconf):
    """
    Handle all *.select params
    """

    for taskParams in bconf.tasks.values():
        paramNames = [x[:x.rfind('.')] for x in taskParams if x.endswith('.select')]

        for name in paramNames:
            handleOneTaskParamSelect(bconf, taskParams, name)
