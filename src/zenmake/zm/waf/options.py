# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Options import OptionsContext as WafOptionsContext
from zm import log

class OptionsContext(WafOptionsContext):
    """ Context for command 'options' """

    def init_logs(self, options, commands, envvars):

        log.enableColorsByCli(options.colors)
        setupOptionVerbose(options)

        # TODO: in debug only mode?
        #if verbose >= 1:
        #    self.load('errcheck')

def setupOptionVerbose(wafOptions):
    """
    Apply a new verbose level to sub modules
    """

    verbose = wafOptions.verbose
    log.setVerbose(verbose)

    if wafOptions.zones:
        log.setZones(wafOptions.zones.split(','))
        if not verbose:
            log.setVerbose(1)
    elif verbose > 0:
        log.setZones(['runner'])

    if verbose > 2:
        log.setZones(['*'])
