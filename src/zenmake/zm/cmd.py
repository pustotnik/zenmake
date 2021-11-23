# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm import log

class Command(object):
    """ Base class for a command outside of waf wscript """

    COLOR = log.colors('NORMAL')

    def __init__(self):
        self._color = log.colors(self.COLOR)

    def _info(self, msg):
        log.info(msg, extra = { 'c1': self._color } )

    def _warn(self, msg):
        log.warn(msg, extra = { 'c1': self._color } )

    def _run(self, cliArgs):
        raise NotImplementedError

    def run(self, cliArgs):
        """ Run command """

        if 'color' in cliArgs:
            log.enableColorsByCli(cliArgs.color)

        return self._run(cliArgs)
