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
from zm.constants import WAF_LOCKFILE

joinpath = path.join

_indyCmd = {
    'zipapp'  : 'zm.zipapp',
    'version' : 'zm.version',
    'sysinfo' : 'zm.sysinfo',
}

def handleCLI(args, noBuildConf, bconfHandler):
    """
    Handle CLI and return command object and waf cmd line
    """
    from zm import cli

    if bconfHandler:
        defaults = dict(bconfHandler.options)
        defaults.update(dict(buildtype = bconfHandler.defaultBuildType))
    else:
        defaults = {}

    cmd, wafCmdLine = cli.parseAll(args, noBuildConf, defaults)
    cli.selected = cmd
    return cmd, wafCmdLine

def isDevVersion():
    """
    Detect that this is development version
    """
    from zm import version
    return version.isDev()

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

def run():
    """
    Prepare and run ZenMake and Waf with ZenMake stuffs
    """

    # use of Options.lockfile is not enough
    os.environ['WAFLOCK'] = WAF_LOCKFILE
    from waflib import Options
    Options.lockfile = WAF_LOCKFILE

    # process buildconf and CLI
    from zm import log, assist, error
    from zm.buildconf import loader as bconfLoader
    from zm.buildconf.handler import ConfHandler as BuildConfHandler

    noBuildConf = True
    cwd = os.getcwd()
    cmd = None

    try:
        # We cannot to know if buildconf is changed if buildroot is unknown.
        # Information about it is stored in the file that is located in buildroot.
        # But buildroot can be set on the command line and we must to parse CLI
        # before processing of buildconf.

        bconfFileName = bconfLoader.findConfFile(cwd)
        noBuildConf = bconfFileName is None
        cmd, wafCmdLine = handleCLI(sys.argv, noBuildConf, None)

        if cmd.name in _indyCmd:
            return runIndyCmd(cmd)

        if noBuildConf:
            log.error('Config buildconf.py/.yaml not found. Check one '
                      'exists in the project directory.')
            return 1

        cliBuildRoot = cmd.args.get('buildroot', None)
        if cliBuildRoot and not os.path.isabs(cliBuildRoot):
            cliBuildRoot = joinpath(cwd, cliBuildRoot)
        buildconf = bconfLoader.load(check = False, dirpath = cwd,
                                     filename = bconfFileName)
        if assist.isBuildConfChanged(buildconf, cliBuildRoot) or isDevVersion():
            bconfLoader.validate(buildconf)
        bconfHandler = BuildConfHandler(buildconf, cliBuildRoot)

        if bconfHandler.options or not ('buildtype' in cmd.args and cmd.args.buildtype):
            # Do parsing of CLI again to apply defaults from buildconf
            cmd, wafCmdLine = handleCLI(sys.argv, noBuildConf, bconfHandler)

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

    # Load waf add-ons to support of custom waf features
    import zm.waf
    zm.waf.loadAllAddOns()

    # start waf ecosystem
    from zm.waf import wrappers
    wrappers.setupAll()

    from zm.waf import launcher
    launcher.run(cwd, cmd, wafCmdLine, bconfHandler)

    return 0
