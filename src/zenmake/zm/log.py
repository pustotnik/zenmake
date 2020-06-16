# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
from waflib import Logs
from zm.constants import PLATFORM
from zm.utils import envValToBool

if not Logs.log:
    Logs.init_log() # pragma: no cover

colors = Logs.colors
colorSettings = Logs.colors_lst

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

    setting = {'yes' : 2, 'auto' : 1, 'no' : 0}[colorArg]
    if setting == 1:
        onTTY = os.environ.get('ZENMAKE_ON_TTY')
        if onTTY:
            onTTY = envValToBool(onTTY)
        else:
            onTTY = sys.stderr.isatty() or sys.stdout.isatty()
        if not onTTY:
            setting = 0

    if setting == 1:
        defaultTerm = 'dumb'
        if PLATFORM == 'windows' and os.name != 'java':
            defaultTerm = ''
        if os.environ.get('TERM', defaultTerm) in ('dumb', 'emacs'):
            setting = 0

    if setting == 1:
        setting = 2

    if setting == 2:
        os.environ['TERM'] = 'vt100'

    colorSettings['USE'] = setting

def colorsEnabled():
    """ Return True if color output is enabled """
    return bool(colorSettings['USE'])

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
