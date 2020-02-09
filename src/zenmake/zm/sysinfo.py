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

from waflib.Configure import ConfigurationContext as WafConfContext, WAF_CONFIG_LOG
from zm.constants import PLATFORM
from zm import log
from zm.cmd import Command as _Command

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
        super(ConfContext, self).__init__(*args, **kwargs)

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

def gatherSysInfo():
    """
    Gather some useful system info.
    """

    # Check that waf wrappers are loaded
    assert 'zm.waf.wrappers' in sys.modules

    import subprocess
    import platform as _platform
    from distutils.spawn import find_executable
    from waflib import Context, Utils
    from waflib import Errors as waferror
    from zm.autodict import AutoDict as _AutoDict

    info = []

    info.append('= System information =')
    info.append('CPU name: %s' % _platform.processor())
    info.append('Bit architecture: %s' % _platform.architecture()[0])
    info.append('Platform: %s' % PLATFORM)
    info.append('Platform id string: %s' % _platform.platform())
    info.append('Python version: %s' % _platform.python_version())
    info.append('Python implementation: %s' % _platform.python_implementation())

    compilers = [
        _AutoDict(header = 'GCC', bin = 'gcc', verargs = ['--version']),
        _AutoDict(header = 'CLANG', bin = 'clang', verargs = ['--version']),
    ]
    for compiler in compilers:
        _bin = find_executable(compiler.bin)
        if _bin:
            ver = subprocess.check_output([_bin] + compiler.verargs,
                                          universal_newlines = True)
            ver = ver.split('\n')[0]
        else:
            ver = 'not recognized'
        info.append('%s: %s' % (compiler.header, ver))

    if Utils.winreg is not None:
        msvcModule = Context.load_tool('msvc')

        cfgCtx = None
        try:
            cfgCtx = ConfContext()
            cfgCtx.prepare()
            version = msvcModule.detect_msvc(cfgCtx)[1]
        except waferror.ConfigurationError:
            version = 'not recognized'
        finally:
            if cfgCtx:
                cfgCtx.finalize()
    else:
        version = 'not recognized'

    info.append('%s: %s' % ('MSVC', version))

    return info

def printSysInfo():
    """
    Print some useful system info. It's for testing mostly.
    """

    print('==================================================')
    for line in gatherSysInfo():
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

        for line in gatherSysInfo():
            self._info(line)
        return 0
