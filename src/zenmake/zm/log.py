# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import Logs

if not Logs.log:
    Logs.init_log() # pragma: no cover

colors = Logs.colors

debug  = Logs.debug
error  = Logs.error
warn   = Logs.warn
info   = Logs.info
pprint = Logs.pprint

makeLogger    = Logs.make_logger
makeMemLogger = Logs.make_mem_logger
freeLogger    = Logs.free_logger

def enableColorsByCli(colorArg):
    """
    Set up log colors by arg from CLI
    """
    setup = {'yes' : 2, 'auto' : 1, 'no' : 0}[colorArg]
    Logs.enable_colors(setup)

def colorsEnabled():
    """ Return True if color output is enabled """
    return bool(Logs.colors_lst['USE'])

def verbose():
    """ Get value of Logs.verbose """
    return Logs.verbose

def setVerbose(value):
    """ Set value of Logs.verbose """
    Logs.verbose = value

def setZones(zones):
    """ Set value of Logs.zones """
    Logs.zones = zones

def printStep(*args, **kwargs):
    """
    Log some step in zenmake command
    """

    extra = kwargs.get('extra', {})
    if 'c1' not in extra:
        extra.update({ 'c1': colors.CYAN })
        kwargs.update({'extra' : extra})
    info(*args, **kwargs)
