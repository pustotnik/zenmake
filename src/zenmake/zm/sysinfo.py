# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import tempfile
import shutil
import atexit

from waflib import Errors as waferror
from waflib.Configure import ConfigurationContext as WafConfContext, WAF_CONFIG_LOG
from zm.constants import PLATFORM
from zm import log, utils
from zm.cmd import Command as _Command
# pylint: disable = unused-import
from zm.waf import wrappers
# pylint: enable = unused-import

_tempdirs = []

def _delTmpDirs():
    for path in _tempdirs:
        if os.path.isdir(path):
            shutil.rmtree(path)
    del _tempdirs[:]

atexit.register(_delTmpDirs)

class ConfContext(WafConfContext):
    """ Special version of ConfigurationContext """

    def __init__(self, *args, **kwargs):

        path = tempfile.mkdtemp(prefix = 'zm.')
        _tempdirs.append(path)

        kwargs['run_dir'] = path
        super().__init__(*args, **kwargs)

        self.top_dir = path
        self.out_dir = os.path.join(path, 'b')

    def prepare_env(self, env):
        pass

    def start_msg(self, *k, **kw):
        pass

    def end_msg(self, *k, **kw):
        pass

    def prepare(self):
        """
        Make ready to use
        """

        self.init_dirs()

        path = os.path.join(self.bldnode.abspath(), WAF_CONFIG_LOG)
        self.logger = log.makeLogger(path, 'cfg')

    def findProgram(self, name):
        """
        Try to find a program
        """
        # pylint: disable = no-member

        try:
            result = self.find_program(name)
        except waferror.WafError:
            result = None
        return result[0] if result else None

def gatherSysInfo(progress = False):
    """
    Gather some useful system info.
    """

    # Check that waf wrappers are loaded
    assert 'zm.waf.wrappers' in sys.modules

    import subprocess
    import multiprocessing
    import platform as _platform
    from waflib import Utils
    from zm.autodict import AutoDict as _AutoDict
    from zm.waf import context

    def printProgress(end = False):
        if progress:
            utils.printInWorkStatus("processing", end)

    cfgCtx = ConfContext()
    cfgCtx.prepare()

    info = []

    info.append('= System information =')
    info.append('CPU name: %s' % _platform.processor())
    info.append('CPU architecture: %s' % _platform.machine())
    info.append('Number of CPUs: %s' % multiprocessing.cpu_count())
    info.append('Bit architecture: %s' % _platform.architecture()[0])
    info.append('Platform: %s' % PLATFORM)
    info.append('Platform id string: %s' % _platform.platform())
    info.append('Python version: %s' % _platform.python_version())
    info.append('Python implementation: %s' % _platform.python_implementation())

    info.append('--------------------')
    info.append('Detected toolchains:')

    def getMsvcVersion():
        if Utils.winreg is not None:
            msvcModule = context.loadTool('msvc')

            try:
                version = msvcModule.detect_msvc(cfgCtx)[1]
            except waferror.ConfigurationError:
                version = 'not recognized'
        else:
            version = 'not recognized'
        return version

    compilers = [
        _AutoDict(header = 'GCC', bin = 'gcc', verargs = ['--version']),
        _AutoDict(header = 'CLANG', bin = 'clang', verargs = ['--version']),
        _AutoDict(header = 'MSVC', func = getMsvcVersion),
        _AutoDict(header = 'DMD', bin = 'dmd', verargs = ['--version']),
        _AutoDict(header = 'LDC', bin = 'ldc2', verargs = ['--version']),
        _AutoDict(header = 'GDC', bin = 'gdc', verargs = ['--version']),
        _AutoDict(header = 'GFORTRAN', bin = 'gfortran', verargs = ['--version']),
        _AutoDict(header = 'IFORT', bin = 'ifort', verargs = ['--version']),
    ]

    for compiler in compilers:
        printProgress()
        if 'func' in compiler:
            ver = compiler.func()
        else:
            _bin = cfgCtx.findProgram(compiler.bin)
            if _bin:
                ver = subprocess.check_output([_bin] + compiler.verargs,
                                              universal_newlines = True)
                ver = ver.split('\n')[0]
            else:
                ver = 'not recognized'
        info.append('%s: %s' % (compiler.header, ver))

    cfgCtx.finalize()

    printProgress(end = True)
    return info

def printSysInfo():
    """
    Print some useful system info. It's for testing mostly.
    """

    print('==================================================')
    for line in gatherSysInfo(progress = True):
        print(line)
    print('==================================================')

class Command(_Command):
    """
    Print sys info.
    It's implementation of command 'sysinfo'.
    """

    def _run(self, cliArgs):

        if cliArgs.verbose >= 1:
            #TODO: add more info
            pass

        for line in gatherSysInfo(progress = True):
            self._info(line)
        return 0
