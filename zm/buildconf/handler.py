# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 There are functions and classes specific to process with our wscript.
"""

import os
from copy import deepcopy
from zm.pyutils import maptype, stringtype, viewitems, viewvalues
from zm import utils, toolchains, log
from zm.autodict import AutoDict
from zm.error import ZenMakeError, ZenMakeLogicError
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

    __slots__ = ('cmdLineHandled', '_conf', '_platforms', '_meta', '_confpaths')

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

        # NOTICE: this method should not have any heavy operations

        allBuildTypes = set(self._conf.buildtypes.keys())
        for taskParams in viewvalues(self._conf.tasks):
            taskBuildTypes = taskParams.get('buildtypes', {})
            allBuildTypes.update(taskBuildTypes.keys())
        self._meta.buildtypes.allnames = allBuildTypes

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

                #current = taskParams.get(paramName, [])
                #current = utils.toList(current)
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

    def _getRealBuildType(self, buildtype):

        if 'map' not in self._meta.buildtypes:
            btMap = dict()
            buildtypes = dict()
            buildtypes.update(self._conf.buildtypes)
            for btype in self._meta.buildtypes.allnames:
                if btype not in buildtypes:
                    buildtypes[btype] = {}
            for btype, val in viewitems(buildtypes):
                btVal = val
                btKey = btype
                while not isinstance(btVal, maptype):
                    if not isinstance(btVal, stringtype):
                        raise ZenMakeError("Invalid type of buildtype value '%s'"
                                           % type(btVal))
                    btKey = btVal
                    if btKey not in buildtypes:
                        raise ZenMakeError("Build type '%s' was not found, check "
                                           "your config." % btKey)
                    btVal = buildtypes[btKey]
                    if btKey == btype and btVal == val:
                        raise ZenMakeError("Circular reference was found")

                btMap[btype] = btKey

            self._meta.buildtypes.map = btMap

        btype = self._meta.buildtypes.map.get(buildtype, None)
        if not btype:
            raise ZenMakeError("Build type '%s' doesn't not exist"
                               " in buildconf." % buildtype)

        return btype

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

        self._meta.buildtypes.selected = self._getRealBuildType(buildtype)

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
    def defaultBuildType(self):
        """ Get calculated default build type """

        if 'default' in self._meta.buildtypes:
            return self._meta.buildtypes.default

        buildtype = self._conf.buildtypes.get('default', '')
        if PLATFORM in self._platforms:
            buildtype = self._platforms[PLATFORM].get('default', buildtype)

        if buildtype and buildtype not in self._meta.buildtypes.allnames:
            raise ZenMakeError("Default build type '%s' was not found, "
                               "check your config." % buildtype)

        self._meta.buildtypes.default = buildtype
        return buildtype

    @property
    def selectedBuildType(self):
        """ Get selected build type """

        self._checkCmdLineHandled()
        return self._meta.buildtypes.selected

    @property
    def supportedBuildTypes(self):
        """
        Get calculated list of supported build types
        """

        if 'supported' in self._meta.buildtypes:
            return self._meta.buildtypes.supported

        supported = set()
        # handle 'buildconf.platforms'
        if PLATFORM in self._platforms:
            validBuildTypes = self._platforms[PLATFORM].get('valid', [])
            if not validBuildTypes:
                raise ZenMakeError("No valid build types for platform '%s' "
                                   "in config" % PLATFORM)
            for btype in validBuildTypes:
                if btype not in self._meta.buildtypes.allnames:
                    raise ZenMakeError("Build type '%s' for platform '%s' "
                                       "was not found, check your config." %
                                       (btype, PLATFORM))
            supported = set(validBuildTypes)
        else:
            supported.update(self._meta.buildtypes.allnames)

        if 'default' in supported:
            supported.remove('default')
        self._meta.buildtypes.supported = sorted(supported)

        return self._meta.buildtypes.supported

    @property
    def tasks(self):
        """
        Get all handled build tasks
        """

        self._checkCmdLineHandled()

        buildtype = self.selectedBuildType
        if buildtype in self._meta.tasks:
            return self._meta.tasks[buildtype]

        tasks = {}

        for taskName, taskParams in viewitems(self._conf.tasks):
            task = {}
            tasks[taskName] = task

            # 1. Copy exising params of selected buildtype from 'buildtypes'
            task.update(self._conf.buildtypes.get(buildtype, {}))

            # 2. Copy/replace existing params from origin task
            task.update(taskParams)
            if 'buildtypes' in task:
                del task['buildtypes']
            # 3. Copy/replace exising params of selected buildtype from 'tasks'
            taskBuildTypes = taskParams.get('buildtypes', {})
            taskBuildParams = taskBuildTypes.get(buildtype, {})
            task.update(taskBuildParams)

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
                raise ZenMakeError("Toolchain '%s': field 'kind' not found" % name)

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
