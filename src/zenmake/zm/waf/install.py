# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os

# NOTICE:This module must import modules with original Waf context classes
# before declaring their alter implementions.
# Otherwise classes in this module can be ignored. In normal case of
# using of the Waf such classes are created in the 'wscript' because this
# file is loaded always after all Waf context classes.

from waflib.Build import INSTALL, UNINSTALL
from zm import error
from zm.waf.build import BuildContext

############ InstallContext

class InstallContext(BuildContext):
    """ Context for command 'install' """

    cmd = 'install'

    def __init__(self, **kw):
        super(InstallContext, self).__init__(**kw)
        self.is_install = INSTALL

    @staticmethod
    def _wrapInstTaskRun(method):

        isdir = os.path.isdir

        def execute(self):

            # Make more user-friendly error report

            isInstall = self.generator.bld.is_install
            if isInstall:
                for output in self.outputs:
                    dirpath = output.parent.abspath()
                    try:
                        if isInstall == INSTALL:
                            os.makedirs(dirpath)
                    except OSError as ex:
                        # It can't be checked before call of os.makedirs because
                        # tasks work in parallel.
                        if not isdir(dirpath): # exist_ok
                            raise error.ZenMakeError(str(ex))

                    if isdir(dirpath) and not os.access(dirpath, os.W_OK):
                        raise error.ZenMakeError('Permission denied: ' + dirpath)

            method(self)

        return execute

    def execute(self):

        from waflib.Errors import WafError
        from waflib.Build import inst

        inst.run = InstallContext._wrapInstTaskRun(inst.run)

        try:
            super(InstallContext, self).execute()
        except WafError as ex:

            # Cut out only error message

            msg = ex.msg.splitlines()[-1]
            prefix = 'ZenMakeError:'
            if not msg.startswith(prefix):
                raise
            msg = msg[len(prefix):].strip()
            raise error.ZenMakeError(msg)

############ UninstallContext

class UninstallContext(InstallContext):
    """ Context for command 'uninstall' """

    cmd = 'uninstall'

    def __init__(self, **kw):
        super(UninstallContext, self).__init__(**kw)
        self.is_install = UNINSTALL
