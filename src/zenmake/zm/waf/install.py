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

from waflib import Node, Options
from waflib.Build import INSTALL, UNINSTALL, inst as InstallTask
from zm import error
from zm.utils import asmethod, substVars
from zm.waf.build import BuildContext

joinpath = os.path.join
normpath = os.path.normpath
isabspath = os.path.isabs
isdir = os.path.isdir

############ InstallContext

class InstallContext(BuildContext):
    """ Context for command 'install' """

    cmd = 'install'

    def __init__(self, **kw):
        super(InstallContext, self).__init__(**kw)
        self.is_install = INSTALL

    def execute(self):

        try:
            super(InstallContext, self).execute()
        except error.WafError as ex:

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

############ 'inst' Task overriding

@asmethod(InstallTask, 'get_install_path')
def _instTaskGetInstallPath(self, destdir = True):

    env = self.env
    zmTaskParams = getattr(self.generator, 'zm-task-params', {})
    substvars = zmTaskParams.get('substvars')
    if substvars:
        env = env.derive()
        env.update(substvars)

    if isinstance(self.install_to, Node.Node):
        dest = self.install_to.abspath()
    else:
        dest = normpath(substVars(self.install_to, env))

    if not isabspath(dest):
        dest = joinpath(env.PREFIX, dest)

    optdestdir = Options.options.destdir
    if destdir and optdestdir:
        dest = joinpath(optdestdir, os.path.splitdrive(dest)[1].lstrip(os.sep))

    return dest

@asmethod(InstallTask, 'run', wrap = True, callOrigFirst = False)
def _instTaskRun(self):

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
