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
from waflib.Task import ASK_LATER as TASK_ASK_LATER, RUN_ME as TASK_RUN_ME
from waflib.Build import INSTALL, UNINSTALL, inst as WafInstallTask
from zm import error, log
from zm.pyutils import stringtype
from zm.pathutils import getNativePath, makePathsConf, substPathsConf, getNodesFromPathsConf
from zm.autodict import AutoDict
from zm.utils import substVars, hashObj
from zm.waf.build import BuildContext

joinpath = os.path.join
normpath = os.path.normpath
relpath = os.path.relpath
dirname = os.path.dirname
isabspath = os.path.isabs
pathexists  = os.path.exists
pathlexists  = os.path.lexists
isdir = os.path.isdir
islink = os.path.islink

############ InstallContext

class InstallContext(BuildContext):
    """ Context for command 'install' """

    cmd = 'install'

    def __init__(self, **kw):
        super().__init__(**kw)
        self.is_install = INSTALL
        self.buildWorkDirName = ''

    def execute(self):

        try:
            super().execute()
        except error.WafError as ex:

            # Cut out only error message

            msg = ex.msg.splitlines()[-1]
            prefix = 'ZenMakeError:'
            if not msg.startswith(prefix):
                raise
            msg = msg[len(prefix):].strip()
            raise error.ZenMakeError(msg)

    def setUpInstallFiles(self, taskParams):
        """
        Setup extra install files
        """

        if not taskParams.get('install-files'):
            return

        kwargs = {
            'type' : 'massive-install-files',
            'features' : 'install_task',
            'zm-task-params' : taskParams,
            'install_to' : True, # to allow task in add_install_task
            'install_from' : True, # to allow task in add_install_task
        }

        self(**kwargs)

############ UninstallContext

class UninstallContext(InstallContext):
    """ Context for command 'uninstall' """

    cmd = 'uninstall'

    def __init__(self, **kw):
        super().__init__(**kw)
        self.is_install = UNINSTALL

############ 'inst' Task overriding

class inst(WafInstallTask):
    """
    Overriding of waflib.Build.inst
    """

    # pylint: disable = invalid-name, no-member

    def __init__(self, *args, **kwargs):
        self.install_user = None
        self.install_group = None
        self.chmod = 0o644

        super().__init__(*args, **kwargs)

        self.zmTaskParams = getattr(self.generator, 'zm-task-params', {})
        self._actions = []
        self._substEnv = None
        self._uid = None
        self._ctxnodes = None

    def _initNodes(self):

        # Waf Node class is not thread safe and nodes from build ctx cannot be
        # safely used in task.run method so here is making of separated nodes.

        class _CtxEmu(object):
            def __init__(self, rootNode):
                self.root = rootNode
                self.srcnode = None
                self.bldnode = None
                self.path = None
                self.buildWorkDirName = ''

        ctx = self.generator.bld

        rootNode = Node.Nod3('', None)
        ctxEmu = _CtxEmu(rootNode)
        rootNode.ctx = ctxEmu

        # we don't use find_dir because nodes from ctx must exist already
        makeNode = rootNode.make_node

        ctxEmu.srcnode = srcNode = makeNode(ctx.srcnode.abspath())
        ctxEmu.bldnode = bldNode = makeNode(ctx.bldnode.abspath())
        ctxEmu.path = pathNode = makeNode(self.generator.path.abspath())

        nodes = self._ctxnodes = AutoDict()
        nodes.root      = rootNode
        nodes.launchdir = makeNode(ctx.launch_node().abspath())
        nodes.path      = pathNode
        nodes.startdir  = pathNode
        nodes.srcdir    = srcNode
        nodes.blddir    = bldNode

    def _checkDestDir(self, dirpath):
        isInstall = self.generator.bld.is_install == INSTALL
        try:
            if isInstall:
                os.makedirs(dirpath)
        except OSError as ex:
            # It can't be checked before call of os.makedirs because
            # tasks work in parallel.
            if not isdir(dirpath): # exist_ok
                raise error.ZenMakeError(str(ex))

        if isdir(dirpath) and not os.access(dirpath, os.W_OK):
            raise error.ZenMakeError('Permission denied: ' + dirpath)

    def _getSubstEnv(self):

        if self._substEnv is not None:
            return self._substEnv

        env = self.env
        substvars = self.zmTaskParams.get('substvars')
        if substvars:
            env = env.derive()
            env.update(substvars)

        self._substEnv = env
        return env

    def _getInstallPath(self, path = None, destdir = True):

        if path is None:
            path = self.install_to

        env = self._getSubstEnv()
        if isinstance(path, Node.Node):
            dest = path.abspath()
        else:
            dest = normpath(substVars(getNativePath(path), env))

        if not isabspath(dest):
            dest = joinpath(getNativePath(env.PREFIX), dest)

        optdestdir = Options.options.destdir
        if destdir and optdestdir:
            optdestdir = getNativePath(optdestdir)
            dest = joinpath(optdestdir, os.path.splitdrive(dest)[1].lstrip(os.sep))

        return dest

    def get_install_path(self, destdir = True):
        return self._getInstallPath(destdir = destdir)

    def init_files(self):

        if self.type != 'massive-install-files':
            super().init_files()
            return

        # This method is not used in parallel so not thread safe code can be used here

        self._initNodes()

        actions = []
        for item in self.zmTaskParams.get('install-files', []):
            item = item.copy()
            if item['do'] == 'symlink':
                dst = item.pop('symlink')
            else:
                dst = item.get('dst')
            item['dst'] = self._getInstallPath(dst)
            actions.append(item)

        self._actions = actions

    def uid(self):

        if self._uid is not None:
            return self._uid

        if self.type != 'massive-install-files':
            lst = self.inputs + self.outputs + [self.link, self.generator.path.abspath()]
        else:
            lst = [self.zmTaskParams['name']]
            lst.extend(self._actions)
            lst.append(self.generator.path.abspath())
        self._uid = hashObj(lst)
        return self._uid

    def runnable_status(self):
        # Installation tasks are always executed, so it's not needed to calculate
        # task signatures and other things

        # This method is called from main thread always.

        for task in self.run_after:
            if not task.hasrun:
                return TASK_ASK_LATER
        return TASK_RUN_ME

    def signature(self):
        # should not be called
        assert False
        return 'ZM_INSTALL_TASK'.encode()

    def copy_fun(self, src, tgt):

        try:
            super().copy_fun(src, tgt)
        except EnvironmentError as ex:
            # Reformat Waf error report
            msg = 'Could not install the file %r' % tgt
            if not pathexists(src):
                msg += "\n  File %r does not exist" % src
            elif not os.path.isfile(src):
                msg += "\n  Path %r is not a file" % src
            else:
                msg += "\n %s" % str(ex)
            raise error.WafError(msg)

    def fix_perms(self, tgt):
        try:
            super().fix_perms(tgt)
        except Exception as ex:
            # Reformat Waf error report
            msg = 'Could not set permissions for the file %r' % tgt
            msg += "\n %s" % str(ex)
            raise error.WafError(msg)

    def do_uninstall(self, src, tgt, lbl, **kwargs):
        if pathlexists(tgt):
            super().do_uninstall(src, tgt, lbl, **kwargs)

    def do_unlink(self, src, tgt, **kwargs):
        if pathlexists(tgt):
            super().do_unlink(src, tgt, **kwargs)

    def rm_empty_dirs(self, tgt):
        while tgt:
            tgt = dirname(tgt)
            if not pathexists(tgt):
                continue
            try:
                os.rmdir(tgt)
            except OSError:
                break
            else:
                if not self.generator.bld.progress_bar:
                    c1 = log.colors.NORMAL
                    c2 = log.colors.BLUE
                    log.info('%s- remove %s%s%s', c1, c2, tgt, c1)

    def _handleCopy(self, info, operations):

        src = info['src']
        dst = info['dst']
        self._checkDestDir(dst)

        nodes = self._ctxnodes
        topdir = nodes.srcdir.abspath()
        startdir = nodes.startdir.abspath()

        src = makePathsConf(src, startdir)
        substPathsConf(src, self._getSubstEnv())
        foundNodes = getNodesFromPathsConf(nodes.root.ctx, src, topdir)

        dstDirNode = nodes.root.make_node(dst)
        makeDstNode = dstDirNode.make_node
        allNodes = []
        for node in foundNodes:
            nodePath = node.abspath()
            if isdir(nodePath):
                pattern = '%s/**' % relpath(nodePath, startdir)
                param = [{ 'startdir' : startdir, 'incl' : pattern }]
                files = getNodesFromPathsConf(nodes.root.ctx, param, topdir)
                files = [(x, makeDstNode(x.path_from(node))) for x in files]
                allNodes.extend(files)
            else:
                allNodes.append((node, makeDstNode(node.name)))

        followSymlinks = info.get('follow-symlinks', True)
        for srcNode, dstNode in allNodes:
            operation = info.copy()
            operation['src'] = srcNode
            operation['dst'] = dstNode
            srcNodePath = srcNode.abspath()

            if not followSymlinks and islink(srcNodePath):
                operation['type'] = 'symlink'
                operation['src'] = os.readlink(srcNodePath)

            operations.append(operation)

    def _handleCopyAs(self, info, operations):

        nodes = self._ctxnodes
        src = substVars(info['src'], self._getSubstEnv())
        dst = info['dst']

        if isabspath(src):
            srcNode = nodes.root.make_node(src)
        else:
            srcNode = nodes.path.make_node(src)

        dstNode = nodes.root.make_node(dst)
        self._checkDestDir(dstNode.parent.abspath())

        operation = info.copy()
        operation['src'] = srcNode
        operation['dst'] = dstNode

        followSymlinks = info.get('follow-symlinks', True)
        if not followSymlinks and islink(srcNode.abspath()):
            operation['type'] = 'symlink'
            operation['src'] = os.readlink(srcNode.abspath())

        operations.append(operation)

    def _handleSymlink(self, info, operations):

        self._handleCopyAs(info, operations)
        operation = operations[-1]
        operation['type'] = 'symlink'

        if info.get('relative', False):
            src = operation['src']
            if isinstance(src, Node.Node):
                src = src.abspath()
            dst = operation['dst'].abspath()
            src = relpath(src, dirname(dst))
            operation['src'] = src

    def _doOperations(self, operations):

        ctx = self.generator.bld
        isInstall = ctx.is_install == INSTALL
        copyFunc = self.do_install if isInstall else self.do_uninstall
        slinkFunc = self.do_link if isInstall else self.do_unlink

        launchNode = self._ctxnodes.launchdir
        for operation in operations:

            src = operation['src']
            if isinstance(src, Node.Node):
                copyLabel = src.path_from(launchNode)
                src = src.abspath()
            elif _type != 'symlink':
                copyLabel = relpath(src, launchNode.abspath())

            dst = operation['dst']
            if isinstance(dst, Node.Node):
                dst = dst.abspath()

            if isInstall:
                dirpath = dirname(dst)
                if not isdir(dirpath):
                    os.makedirs(dirpath)

            _type = operation.get('type', 'file')
            self.install_user = operation.get('user', None)
            self.install_group = operation.get('group', None)
            self.chmod = operation.get('chmod', 0o644)
            if isinstance(self.chmod, stringtype):
                self.chmod = int(self.chmod, 8)

            if _type == 'symlink':
                slinkFunc(src, dst)
            else:
                copyFunc(src, dst, copyLabel)

    def run(self):

        if not self.generator.bld.is_install:
            return

        if self.type == 'massive-install-files':
            operations = []
            for action in self._actions:
                actionType = action['do']
                funcName = ''.join([x.capitalize() for x in actionType.split('-')])
                funcName = '_handle%s' % funcName
                func = getattr(self, funcName)
                func(action, operations)
            self._doOperations(operations)
            return

        # Make more user-friendly error report
        for output in self.outputs:
            if output.parent:
                self._checkDestDir(output.parent.abspath())

        super().run()
