# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm.constants import APPNAME
from zm import cmd

_VERSION = '0.2.0'

def current():
    """ Get current version """
    return _VERSION

class Command(cmd.Command):
    """
    Print version of the program.
    It's implementation of command 'version'.
    """

    def _run(self, cliArgs):

        if cliArgs.verbose >= 1:
            #TODO: add more info
            pass

        self._info("{} version {}".format(APPNAME, current()))
        return 0
