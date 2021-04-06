# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import gc

from waflib.Options import OptionsContext as WafOptionsContext
from zm import log

class OptionsContext(WafOptionsContext):
    """ Context for command 'options' """

    def init_logs(self, options, commands, envvars):

        log.enableColorsByCli(options.colors)
        setupOptionVerbose(options)

        # TODO: in debug only mode?
        if options.verbose >= 2:
            self.load('errcheck')

    def execute(self):
        # WafOptionsContext.execute() makes preforked processes so it can
        # be better for general performance to free some memory before it.
        gc.collect()
        super().execute()

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
