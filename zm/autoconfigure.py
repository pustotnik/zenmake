# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
from waflib import Options, Configure
from waflib.ConfigSet import ConfigSet
from zm import utils, log, assist

joinpath = os.path.join

# Force to turn off internal WAF autoconfigure decorator.
# It's just to rid of needless work and to save working time.
Configure.autoconfig = False

def autoconfigure(clicmd, bconfHandler, method):
    """
    Decorator that enables context commands to run *configure* as needed.
    Alternative version.
    """

    def areFilesChanged():
        zmCmn = ConfigSet()
        try:
            zmcmnfile = bconfHandler.confPaths.zmcmnfile
            zmCmn.load(zmcmnfile)
        except EnvironmentError:
            return True

        _hash = 0
        for file in zmCmn.monitfiles:
            try:
                _hash = utils.mkHashOfStrings((_hash, utils.readFile(file, 'rb')))
            except EnvironmentError:
                return True

        return _hash != zmCmn.monithash

    def areBuildTypesNotConfigured():
        buildconf = bconfHandler.conf
        buildtype = clicmd.args.buildtype
        zmcachedir = bconfHandler.confPaths.zmcachedir
        for taskName in buildconf.tasks:
            taskVariant = assist.getTaskVariantName(buildtype, taskName)
            fname = assist.makeCacheConfFileName(zmcachedir, taskVariant)
            if not os.path.exists(fname):
                return True
        return False

    def runconfig(self, env):
        from waflib import Scripting
        Scripting.run_command(env.config_cmd or 'configure')
        Scripting.run_command(self.cmd)

    def execute(self):

        # Execute the configuration automatically
        autoconfig = bconfHandler.conf.features['autoconfig']

        if not autoconfig:
            return method(self)

        autoconfigure.callCounter += 1
        if autoconfigure.callCounter > 10:
            # I some cases due to programming error, user actions or system
            # problems we can get infinite call of current function. Maybe
            # later I'll think up better protection but in normal case
            # it shouldn't happen.
            raise Exception('Infinite recursion was detected')

        env = ConfigSet()
        bconfPaths = bconfHandler.confPaths
        try:
            env.load(joinpath(bconfPaths.buildout, Options.lockfile))
        except EnvironmentError:
            log.warn('Configuring the project')
            return runconfig(self, env)

        if env.run_dir != bconfPaths.buildroot:
            return runconfig(self, env)

        if areFilesChanged():
            return runconfig(self, env)

        if areBuildTypesNotConfigured():
            return runconfig(self, env)

        return method(self)

    return execute

autoconfigure.callCounter = 0
