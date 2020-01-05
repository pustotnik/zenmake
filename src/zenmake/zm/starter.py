# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
import os
from os import path
if sys.hexversion < 0x2070000:
    raise ImportError('Python >= 2.7 is required')

#pylint: disable=wrong-import-position
from zm.constants import WAF_LOCKFILE, CWD

joinpath = path.join

_indyCmd = {
    'zipapp'  : 'zm.zipapp',
    'version' : 'zm.version',
    'sysinfo' : 'zm.sysinfo',
}

def handleCLI(args, noBuildConf, options):
    """
    Handle CLI and return command object and waf cmd line
    """
    from zm import cli

    defaults = options if options else {}
    cmd, wafCmdLine = cli.parseAll(args, noBuildConf, defaults)
    cli.selected = cmd
    return cmd, wafCmdLine

def runIndyCmd(cmd):
    """
    Run independent command that doesn't use buildconf and Waf.
    """

    from zm.utils import loadPyModule

    if cmd.name not in _indyCmd:
        raise NotImplementedError('Unknown command')

    moduleName = _indyCmd[cmd.name]
    module = loadPyModule(moduleName, withImport = True)
    return module.Command().run(cmd.args)

def findTopLevelBuildConfDir(startdir):
    """
    Try to find top level dir with a buildconf file.
    Return None if file was not found.
    """

    from zm.buildconf.loader import findConfFile

    curdir = startdir
    found = None
    while curdir:
        if findConfFile(curdir):
            found = curdir

        nextdir = path.dirname(curdir)
        if nextdir == curdir:
            break
        curdir = nextdir

    return found

def run():
    """
    Prepare and run ZenMake and Waf with ZenMake stuffs
    """

    # use of Options.lockfile is not enough
    os.environ['WAFLOCK'] = WAF_LOCKFILE
    from waflib import Options
    Options.lockfile = WAF_LOCKFILE

    # process buildconf and CLI
    from zm import log, error
    from zm.buildconf.processing import ConfManager as BuildConfManager

    noBuildConf = True
    cwd = CWD
    cmd = None

    try:

        # set up waf wrappers
        from zm.waf import wrappers
        wrappers.setup()

        # We cannot to know if buildconf is changed while buildroot is unknown.
        # This information is stored in the file that is located in buildroot.
        # But buildroot can be set on the command line and we must to parse CLI
        # before processing of buildconf.

        bconfDir = findTopLevelBuildConfDir(cwd)
        noBuildConf = bconfDir is None
        cmd, wafCmdLine = handleCLI(sys.argv, noBuildConf, None)

        if cmd.name in _indyCmd:
            return runIndyCmd(cmd)

        if noBuildConf:
            log.error('Config buildconf.py/.yaml not found. Check one '
                      'exists in the project directory.')
            return 1

        cliBuildRoot = cmd.args.get('buildroot', None)
        if cliBuildRoot and not path.isabs(cliBuildRoot):
            cliBuildRoot = joinpath(cwd, cliBuildRoot)

        bconfManager = BuildConfManager(bconfDir, cliBuildRoot)
        bconf = bconfManager.root

        if bconf.options:
            # Do parsing of CLI again to apply defaults from buildconf
            cmd, wafCmdLine = handleCLI(sys.argv, noBuildConf, bconf.options)

    except error.ZenMakeError as ex:
        verbose = 0
        if cmd:
            verbose = cmd.args.verbose
        if verbose > 1:
            log.pprint('RED', ex.fullmsg)
        log.error(ex.msg)
        sys.exit(1)
    except KeyboardInterrupt:
        log.pprint('RED', 'Interrupted')
        sys.exit(68)

    # start waf ecosystem
    from zm.waf import launcher
    launcher.run(cwd, cmd, wafCmdLine, bconfManager)

    return 0
