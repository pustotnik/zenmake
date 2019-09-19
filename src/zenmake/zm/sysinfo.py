# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import PLATFORM
from zm import cmd

def gatherSysInfo():
    """
    Gather some useful system info.
    """

    import subprocess
    import platform as _platform
    from distutils.spawn import find_executable
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
        _AutoDict(header = 'GCC:', bin = 'gcc', verargs = ['--version']),
        _AutoDict(header = 'CLANG:', bin = 'clang', verargs = ['--version']),
        #TODO: find a way to detect msvc
        #_AutoDict(header = 'MSVC:', bin = 'cl', verargs = []),
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

    return info

def printSysInfo():
    """
    Print some useful system info. It's for testing mostly.
    """

    print('==================================================')
    for line in gatherSysInfo():
        print(line)
    print('==================================================')

class Command(cmd.Command):
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
