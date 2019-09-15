# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 There are functions and classes specific to process with our wscript.
"""

import os
from collections import defaultdict
from copy import deepcopy

from zm.pyutils import viewitems, viewvalues
from zm import utils, toolchains, log
from zm.autodict import AutoDict
from zm.error import ZenMakeError, ZenMakeLogicError, ZenMakeConfError
from zm.constants import PLATFORM

joinpath = os.path.join

def _getBuildTypeFromCLI(clicmd):
    if not clicmd or not clicmd.args.buildtype:
        return ''
    return clicmd.args.buildtype

class BuildConfHandler(object):
    """
    Class to handle data from buildconf
    """

    __slots__ = 'cmdLineHandled', '_conf', '_platforms', '_meta', '_confpaths'

    def __init__(self, conf):

        self.cmdLineHandled = False

        self._conf = conf
        self._platforms = self._conf.platforms

        self._meta = AutoDict()
        # just in case
        self._meta.buildtypes = AutoDict()

        from zm.buildconf.paths import BuildConfPaths
        self._confpaths = BuildConfPaths(conf)
        self._preprocess()

    def _preprocess(self):

        self._handleMatrixBuildtypes()
        self._handleSupportedBuildTypes()
        self._handleDefaultBuildType()

    def _handleTasksEnvVars(self, tasks):

        cinfo         = toolchains.CompilersInfo
        flagVars      = cinfo.allFlagVars()
        toolchainVars = cinfo.allVarsToSetCompiler()

        for taskParams in viewvalues(tasks):
            # handle flags
            for var in flagVars:
                envVal = os.environ.get(var, None)
                if not envVal:
                    continue

                paramName = var.lower()

                #current = utils.toList(taskParams.get(paramName, []))
                # FIXME: should we add or replace?
                #taskParams[paramName] = current + utils.toList(envVal)
                taskParams[paramName] = utils.toList(envVal)

            # handle toolchains
            for var in toolchainVars:
                toolchain = os.environ.get(var, None)
                if not toolchain:
                    continue
                if var.lower() in taskParams.get('features', ''):
                    taskParams['toolchain'] = toolchain

    def _handleMatrixBuildtypes(self):
        destPlatform = PLATFORM
        matrixBuildTypes = defaultdict(set)
        for entry in self._conf.matrix:
            condition = entry.get('for', {})
            buildtypes = utils.toList(condition.get('buildtype', []))
            platforms = utils.toList(condition.get('platform', []))
            if buildtypes:
                if destPlatform in platforms:
                    matrixBuildTypes[destPlatform].update(buildtypes)
                elif not platforms:
                    matrixBuildTypes['all'].update(buildtypes)

            defaultBuildType = entry.get('set', {}).get('default-buildtype', None)
            if defaultBuildType is not None:
                if not platforms or destPlatform in platforms:
                    matrixBuildTypes['default'] = defaultBuildType

        self._meta.matrix.buildtypes = matrixBuildTypes

    def _handleSupportedBuildTypes(self):
        """
        Calculate list of supported build types
        """

        destPlatform = PLATFORM

        supported = set()
        matrixBuildTypes = self._meta.matrix.buildtypes

        platformFound = False
        if destPlatform in self._platforms:
            platformFound = True
            supported = self._platforms[destPlatform].get('valid', [])
            supported = set(supported)
        else:
            supported = set(self._conf.buildtypes.keys())

        if destPlatform in matrixBuildTypes:
            platformFound = True
            supported.update(matrixBuildTypes[destPlatform])

        supported.update(matrixBuildTypes.get('all', set()))

        if 'default' in supported:
            supported.remove('default')

        if platformFound and not supported:
            raise ZenMakeConfError("No valid build types for platform '%s' "
                                   "in config" % destPlatform)
        self._meta.buildtypes.supported = sorted(supported)

    def _handleDefaultBuildType(self):
        """ Calculate default build type """

        buildtype = self._conf.buildtypes.get('default', '')
        if PLATFORM in self._platforms:
            buildtype = self._platforms[PLATFORM].get('default', buildtype)
        buildtype = self._meta.matrix.buildtypes.get('default', buildtype)

        if buildtype and buildtype not in self.supportedBuildTypes:
            errmsg = "Invalid config value."
            errmsg += " Default build type '%s' is not supported." % buildtype
            errmsg += " Supported values: %s" % str(self.supportedBuildTypes)[1:-1]
            raise ZenMakeConfError(errmsg)

        self._meta.buildtypes.default = buildtype

    def _checkCmdLineHandled(self):
        if not self.cmdLineHandled:
            raise ZenMakeLogicError("Command line args wasn't handled yet. "
                                    "You should call method handleCmdLineArgs.")

    def handleCmdLineArgs(self, clicmd):
        """
        Apply values from command line
        """

        buildtype = _getBuildTypeFromCLI(clicmd)

        supportedBuildTypes = self.supportedBuildTypes
        if buildtype not in supportedBuildTypes:
            raise ZenMakeError("Invalid choice for build type: '%s', "
                               "(choose from %s)" %
                               (buildtype, str(supportedBuildTypes)[1:-1]))

        self._meta.buildtypes.selected = buildtype
        self._meta.buildtype.dir = joinpath(self._confpaths.buildout, buildtype)
        self.cmdLineHandled = True

    @property
    def conf(self):
        """ Get buildconf """
        return self._conf

    @property
    def projectName(self):
        """ Get project name """
        return self._conf.project['name']

    @property
    def projectVersion(self):
        """ Get project version """
        return self._conf.project['version']

    @property
    def confPaths(self):
        """ Get object of class BuildConfPaths """
        return self._confpaths

    @property
    def supportedBuildTypes(self):
        """ Get calculated list of supported build types """
        return self._meta.buildtypes.supported

    @property
    def defaultBuildType(self):
        """ Get calculated default build type """
        return self._meta.buildtypes.default

    @property
    def selectedBuildType(self):
        """ Get selected build type """

        self._checkCmdLineHandled()
        return self._meta.buildtypes.selected

    @property
    def selectedBuildTypeDir(self):
        """ Get selected build type directory """

        self._checkCmdLineHandled()
        return self._meta.buildtype.dir

    @property
    def tasks(self):
        """
        Get all handled build tasks
        """

        self._checkCmdLineHandled()

        buildtype = self.selectedBuildType
        if buildtype in self._meta.tasks:
            return self._meta.tasks[buildtype]

        # gather all task names
        allTaskNames = list(self._conf.tasks.keys())
        for entry in self._conf.matrix:
            allTaskNames.extend(utils.toList(entry.get('for', {}).get('task', [])))
        allTaskNames = tuple(set(allTaskNames))

        tasks = {}

        for taskName in allTaskNames:

            task = tasks.setdefault(taskName, {})
            # 1. Copy existing params from origin task
            task.update(self._conf.tasks.get(taskName, {}))
            # 2. Copy/replace exising params of selected buildtype from 'buildtypes'
            task.update(self._conf.buildtypes.get(buildtype, {}))

        destPlatform = PLATFORM
        for entry in self._conf.matrix:
            condition = entry.get('for', None)
            if condition is None:
                log.warn("WARN: In buildconf.matrix found item without 'for'. "
                         "It's probably a mistake.")
                condition = {}
            params = entry.get('set', {})
            params.pop('default-buildtype', None)

            condTasks = utils.toList(condition.get('task', []))
            condBuildtypes = utils.toList(condition.get('buildtype', []))
            condPlatforms = utils.toList(condition.get('platform', []))

            if condBuildtypes and buildtype not in condBuildtypes:
                continue
            if condPlatforms and destPlatform not in condPlatforms:
                continue

            if not condTasks:
                condTasks = allTaskNames

            for taskName in condTasks:
                task = tasks.setdefault(taskName, {})
                task.update(params)

        self._handleTasksEnvVars(tasks)

        self._meta.tasks[buildtype] = tasks
        return tasks

    @property
    def toolchainNames(self):
        """
        Get unique names of all toolchains from current build tasks
        """

        if 'names' in self._meta.toolchains:
            return self._meta.toolchains.names

        self._checkCmdLineHandled()

        # gather unique names
        _toolchains = set()
        for taskParams in viewvalues(self.tasks):
            tool = taskParams.get('toolchain', None)
            if tool:
                _toolchains.add(tool)

        _toolchains = tuple(_toolchains)
        self._meta.toolchains.names = _toolchains
        return _toolchains

    @property
    def customToolchains(self):
        """
        Get 'custom' toolchains.
        """

        if 'custom' in self._meta.toolchains:
            return self._meta.toolchains.custom

        srcToolchains = self._conf.toolchains
        _customToolchains = AutoDict()
        for name, info in viewitems(srcToolchains):
            _vars = deepcopy(info) # don't change origin
            kind = _vars.pop('kind', None)
            if kind is None:
                raise ZenMakeConfError("Toolchain '%s': field 'kind' not found" % name)

            for k, v in viewitems(_vars):
                # try to identify path and do warning if not
                path = utils.unfoldPath(self._confpaths.projectroot, v)
                if not os.path.exists(path):
                    log.warn("Path to toolchain '%s' doesn't exists" % path)
                _vars[k] = path

            _customToolchains[name].kind = kind
            _customToolchains[name].vars = _vars

        self._meta.toolchains.custom = _customToolchains
        return _customToolchains
