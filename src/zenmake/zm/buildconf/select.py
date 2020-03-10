# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

from zm.constants import PLATFORM, KNOWN_PLATFORMS, CPU_ARCH
from zm.pyutils import viewitems, viewvalues
from zm.utils import toList
from zm.error import ZenMakeLogicError, ZenMakeConfError
from zm.buildconf.scheme import KNOWN_CONDITION_PARAM_NAMES
from zm.features import areFeaturesLoaded
from zm.toolchains import getAllNames as getAllToolchainNames

_local = {}

def _getReadyConditions():

    conditions = _local.get('ready-conditions')
    if conditions is not None:
        return conditions

    if not areFeaturesLoaded():
        msg = "Programming error: task features have not been loaded yet"
        raise ZenMakeLogicError(msg)

    conditions = {}

    # platform conditions
    for platform in KNOWN_PLATFORMS:
        conditions[platform] = dict(platform = (platform, ))

    for toolchain in getAllToolchainNames(platform = 'all'):
        assert toolchain not in conditions
        conditions[toolchain] = dict(toolchain = (toolchain, ))

    _local['ready-conditions'] = conditions
    return conditions

def handleOneTaskParamSelect(bconf, taskParams, paramName):
    """
    Handle one <param name>.select
    """

    selectName = '%s.select' % paramName

    selectParam = taskParams.get(selectName)
    if selectParam is None:
        return

    sysStates = (
        ('platform', PLATFORM),
        ('cpu-arch', CPU_ARCH),
    )

    buildtype = bconf.selectedBuildType

    def tryToSelect(conditions, condName, taskParams):
        # pylint: disable = too-many-return-statements

        condition = conditions.get(condName)
        if condition is None:
            condition = _getReadyConditions().get(condName)
        if condition is None:
            msg = "Error in the task %r: " % taskParams['name']
            msg += "there is no condition %r in buildconf.conditions" % condName
            raise ZenMakeConfError(msg)

        # check we didn't forget any param
        assert frozenset(condition.keys()) <= KNOWN_CONDITION_PARAM_NAMES

        # check system states
        for name, val in sysStates:
            filterVals = condition.get(name)
            if filterVals is not None and val not in filterVals:
                return False

        # check task
        filterVals = condition.get('task')
        if filterVals is not None and taskParams['name'] not in filterVals:
            return False

        # check buildtype
        filterVals = condition.get('buildtype')
        if filterVals is not None and buildtype not in filterVals:
            return False

        # check toolchain
        filterVals = condition.get('toolchain')
        if filterVals is not None:
            if paramName == 'toolchain':
                msg = "Error in the task %r: " % taskParams['name']
                msg += "Condition %r in buildconf.conditions" % condName
                msg += " can not be used to select toolchain because it"
                msg += " contains 'toolchain'"
                raise ZenMakeConfError(msg)

            filterVals = set(filterVals)
            taskToolchains = toList(taskParams.get('toolchain', []))
            if not filterVals.issubset(taskToolchains):
                return False

        # check system env vars
        filterVals = condition.get('environ', {})
        for var, val in viewitems(filterVals):
            if os.environ.get(var) != val:
                return False

        return True

    defaultValue = selectParam.get('default', taskParams.get(paramName))
    detectedValue = None

    for label, param in viewitems(selectParam):
        if label == 'default':
            continue

        # try one record of conditions
        paramConditions = label.split()
        for condName in paramConditions:
            if not tryToSelect(bconf.conditions, condName, taskParams):
                break
        else:
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

    for taskParams in viewvalues(bconf.tasks):
        paramNames = [x[:x.rfind('.')] for x in taskParams if x.endswith('.select')]

        for name in paramNames:
            handleOneTaskParamSelect(bconf, taskParams, name)
