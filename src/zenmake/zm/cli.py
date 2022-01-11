# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
from collections import defaultdict

# argparse from the https://pypi.org/project/argparse/ supports aliases
from thirdparty.argparse import argparse
from zm.constants import APPNAME, CAP_APPNAME, PLATFORM, CWD
from zm.pyutils import maptype, struct
from zm.pathutils import unfoldPath
from zm.utils import envValToBool
from zm import log
from zm.error import ZenMakeLogicError
from zm.autodict import AutoDict as _AutoDict

ParsedCommand = struct('ParsedCommand', 'name, args, notparsed, orig')

"""
Object of ParsedCommand with current command after last parsing of command line.
This variable can be changed outside and is used to get CLI command and args.
"""
selected = None

"""
Contains configurable 'commands', 'options' and 'posargs'
"""
config = _AutoDict()

class Command(_AutoDict):
    """ Class to set up a command for CLI """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setdefault('aliases', [])
        self.setdefault('usageTextTempl', "%s [options]")

# Declarative list of commands in CLI
config.commands = [
    Command(
        name = 'help',
        description = 'show help for a given topic or a help overview',
        usageTextTempl = "%s [command/topic]",
    ),
    Command(
        name = 'configure',
        aliases = ['cnf', 'cfg'],
        description = 'configure project',
    ),
    Command(
        name = 'build',
        aliases = ['bld'],
        description = 'build project',
        usageTextTempl = "%s [options] [task [task] ... ]",
    ),
    Command(
        name = 'test',
        cmdBefore = 'build', # this command must be always in pair with 'build'
        description = 'build and run tests',
        usageTextTempl = "%s [options] [task [task] ... ]",
    ),
    Command(
        name = 'run',
        cmdBefore = 'build', # this command must be always in pair with 'build'
        description = 'build and run executable task/target',
        usageTextTempl = "%s [options] [task] [-- program args]",
    ),
    Command(
        name = 'clean',
        aliases = ['c'],
        description = 'clean project',
    ),
    Command(
        name = 'cleanall',
        aliases = ['C'],
        description = 'removes the build directory with everything in it',
    ),
    Command(
        name = 'distclean',
        aliases = ['dc'],
        description = 'the same as the "cleanall" command',
    ),
    Command(
        name = 'install',
        description = 'installs the targets on the system',
    ),
    Command(
        name = 'uninstall',
        description = 'removes the targets installed',
    ),
    Command(
        name = 'zipapp',
        description = 'make executable zip archive of %s' % APPNAME,
    ),
    Command(
        name = 'version',
        aliases = ['ver'],
        description = 'print version of %s' % APPNAME,
    ),
    Command(
        name = 'sysinfo',
        description = 'print some system info useful for diagnostic reasons',
    ),
]

# map: cmd name/alias -> Command
def _makeCmdNameMap():
    cmdNameMap = {}
    for cmd in config.commands:
        cmdNameMap[cmd.name] = cmd
        for alias in cmd.aliases:
            cmdNameMap[alias] = cmd
    return cmdNameMap

class PosArg(_AutoDict):
    """ Class to set up positional param for CLI """

    NOTARGPARSE_FIELDS = ('name', 'commands')

# Declarative list of positional args after command name in CLI
config.posargs = [
    # global options that are used before command in cmd line
    PosArg(
        name = 'tasks',
        nargs = '*', # optional list of args
        default = [],
        help = 'select tasks from buildconf, all tasks if nothing is selected',
        commands = ['build', 'test'],
    ),
    PosArg(
        name = 'task',
        nargs = '?', # one optional arg
        help = 'set task name from buildconf or target name',
        commands = ['run',],
    ),
]

class Option(_AutoDict):
    """ Class to set up an option for CLI """

    NOTARGPARSE_FIELDS = ('names', 'commands', 'runcmd', 'isglobal')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setdefault('isglobal', False)
        self.setdefault('commands', [])
        self.setdefault('action', 'store')
        self.setdefault('type', None)
        self.setdefault('choices', None)
        self.setdefault('default', None)

# All commands which depend on parameters from buildconf.
# Also these are all commands that can call 'configure' cmd + 'configure'.
ALL_CONF_CMD_NAMES = [
    'configure', 'build', 'test', 'run', 'install', 'uninstall'
]

# Declarative list of options in CLI
# Special param 'runcmd' is used to declare option that runs another command
# before current. There is no need to set 'action' in that case. And it cannot
# be used for global options, of course.
# See also *_init.py in zm.features for extra options
config.options = [
    # global options that are used before command in cmd line
    Option(
        names = ['-h', '--help'],
        isglobal = True,
        action = 'help',
        help = 'show this help message and exit',
    ),
    Option(
        names = ['--version'],
        isglobal = True,
        runcmd = 'version',
        help = 'alias for command "version"',
    ),
    # command options
    Option(
        names = ['-h', '--help'],
        action = 'help',
        commands = [x.name for x in config.commands], # for all commands
        help = 'show this help message for command and exit',
    ),
    Option(
        names = ['-b', '--buildtype'],
        commands = ['configure', 'build', 'clean', 'test', 'run',
                    'install', 'uninstall', ],
        help = 'set the build type',
    ),
    Option(
        names = ['-g', '--configure'],
        commands = ['build', 'test', 'run', 'install'],
        runcmd = 'configure',
    ),
    Option(
        names = ['-c', '--clean'],
        commands = ['build', 'test', 'run', 'install'],
        runcmd = 'clean',
    ),
    Option(
        names = ['-a', '--clean-all'],
        dest = 'cleanall',
        commands = ['configure', 'build', 'test', 'run', 'install'],
        runcmd = 'cleanall',
    ),
    Option(
        names = ['-d', '--distclean'],
        commands = ['configure', 'build', 'test', 'run', 'install'],
        runcmd = 'distclean',
    ),
    Option(
        names = ['-j', '--jobs'],
        type = int,
        commands = ['build', 'test', 'run', 'install'],
        help = 'amount of parallel jobs',
    ),
    Option(
        names = ['-p', '--progress'],
        action = "store_true",
        commands = ['build', 'test', 'run', 'install', 'uninstall'],
        help = 'progress bar',
    ),
    Option(
        names = ['-f', '--force'],
        action = "store_true",
        commands = ['configure', ],
        help = 'force command',
    ),
    Option(
        names = ['-o', '--buildroot'],
        commands = ALL_CONF_CMD_NAMES + ['clean', 'cleanall', 'distclean'],
        help = "build directory for the project",
    ),
    Option(
        names = ['-E', '--force-edeps'],
        dest = 'forceExternalDeps',
        action = "store_true",
        commands = ['configure', 'build', 'test', 'run', 'clean',
                    'install', 'uninstall'],
        help = "force rules for external dependencies",
    ),
    Option(
        names = ['-H', '--cache-cfg-actions'],
        dest = 'cacheCfgActionResults',
        action = "store_true",
        commands = ALL_CONF_CMD_NAMES,
        help = "cache results of config actions",
    ),
    Option(
        names = ['--destdir'],
        commands = ['zipapp', 'install', 'uninstall'],
        help = 'destination directory',
    ),
    Option(
        names = ['--prefix'],
        commands = ALL_CONF_CMD_NAMES, # it must be in all these commands
        help = 'installation prefix',
    ),
    Option(
        names = ['--bindir'],
        commands = ALL_CONF_CMD_NAMES, # it must be in all these commands
        help = 'installation bin directory [ ${PREFIX}/bin ]',
    ),
    Option(
        names = ['--libdir'],
        commands = ALL_CONF_CMD_NAMES, # it must be in all these commands
        help = 'installation lib directory [ ${PREFIX}/lib[64] ]',
    ),
    Option(
        names = ['-v', '--verbose'],
        action = "count",
        commands = [x.name for x in config.commands if x.name != 'help'],
        help = 'verbosity level -v -vv or -vvv',
    ),
    Option(
        names = ['-A', '--verbose-configure'],
        dest = 'verboseConfigure',
        action = "count",
        commands = ALL_CONF_CMD_NAMES,
        help = 'verbosity level -A -AA or -AAA for configure stage',
    ),
    Option(
        names = ['-B', '--verbose-build'],
        dest = 'verboseBuild',
        action = "count",
        commands = ['build', 'install', 'uninstall', 'test', 'run'],
        help = 'verbosity level -B -BB or -BBB for build stage',
    ),
    Option(
        names = ['--color'],
        choices = ('yes', 'no', 'auto'),
        commands = [x.name for x in config.commands \
                            if x.name not in ('version', 'sysinfo')],
        help = 'whether to use colors (yes/no/auto)',
    ),
]

DEFAULT_PREFIX = '/usr/local'
if PLATFORM == 'windows':
    import tempfile
    d = tempfile.gettempdir()
    # windows preserves the case, but gettempdir does not
    DEFAULT_PREFIX = d[0].upper() + d[1:]

config.optdefaults = {
    'verbose': 0,
}

def _getReadyOptDefaults():

    # These params should be obtained only before parsing but
    # not when current python has loaded.
    _getenv = os.environ.get
    config.optdefaults.update({
        'color': _getenv('NOCOLOR', '') and 'no' or 'auto',
        'destdir' : {
            'any': _getenv('DESTDIR', ''),
            'zipapp' : _getenv('DESTDIR', '.'),
        },
        'buildroot' : _getenv('BUILDROOT', None),
        'prefix' : _getenv('PREFIX', '') or DEFAULT_PREFIX,
        'bindir' : _getenv('BINDIR', None),
        'libdir' : _getenv('LIBDIR', None),
        'cache-cfg-actions' : envValToBool(_getenv('ZM_CACHE_CFGACTIONS')),
    })

    return config.optdefaults

class CmdLineParser(object):
    """
    CLI for ZenMake.
    WAF has own CLI and it could be used but I wanted to have a different CLI.
    """

    __slots__ = (
        '_defaults', '_globalOptions', '_command', '_wafCmdLine',
        '_parser', '_commandHelps', '_cmdNameMap', '_origArgs',
    )

    def __init__(self, progName, defaults):

        self._defaults = defaultdict(dict)
        self._defaults.update(_getReadyOptDefaults())
        self._defaults.update(defaults)

        self._command = None
        self._origArgs = None
        self._wafCmdLine = []

        self._setupOptions()
        self._cmdNameMap = _makeCmdNameMap()

        class MyHelpFormatter(argparse.HelpFormatter):
            """ Some customization"""
            def __init__(self, prog):
                super().__init__(prog, max_help_position = 27)
                self._action_max_length = 23

        kwargs = dict(
            prog = progName,
            formatter_class = MyHelpFormatter,
            description = '%s: build system based on the Waf build system' % CAP_APPNAME,
            usage = "%(prog)s <command> [options] [args]",
            add_help = False
        )
        self._parser = argparse.ArgumentParser(**kwargs)

        groupGlobal = self._parser.add_argument_group('global options')
        self._addOptions(groupGlobal, cmd = None)

        kwargs = dict(
            title = 'list of commands',
            help = '', metavar = '', dest = 'command'
        )
        subparsers = self._parser.add_subparsers(**kwargs)

        commandHelps = _AutoDict()
        helpCmd = None
        for cmd in config.commands:
            commandHelps[cmd.name] = _AutoDict()
            cmdHelpInfo = commandHelps[cmd.name]
            cmdHelpInfo.usage = self._makeCmdUsageText(progName, cmd)
            cmdHelpInfo.help = cmd.description
            cmdHelpInfo.description = cmd.description.capitalize()
            cmdHelpInfo.aliases = cmd.aliases

            if cmd.name == 'help': # It will be processed below
                helpCmd = cmd
                continue

            kwargs = cmdHelpInfo
            kwargs['add_help'] = False
            cmdParser = subparsers.add_parser(cmd.name, **kwargs)

            self._addCmdPosArgs(cmdParser, cmd)

            groupCmdOpts = cmdParser.add_argument_group('command options')
            self._addOptions(groupCmdOpts, cmd = cmd)
            cmdHelpInfo.help = cmdParser.format_help()

        # special case for 'help' command
        if helpCmd is None:
            raise ZenMakeLogicError("Programming error: no command "
                                    "'help' in config.commands") # pragma: no cover
        cmd = helpCmd
        kwargs = commandHelps[cmd.name]
        kwargs['add_help'] = True
        cmdParser = subparsers.add_parser(cmd.name, **kwargs)
        cmdParser.add_argument('topic', nargs='?', default = 'overview')

        self._commandHelps = commandHelps

    def _setupOptions(self):
        self._globalOptions = [x for x in config.options if x.isglobal]

    def _getOptionDefault(self, opt, cmd  = None):
        optName = opt.names[-1].replace('-', '', 2)
        val = self._defaults.get(optName, None)
        if isinstance(val, maptype):
            cmd = 'any' if cmd is None else cmd.name
            val = val.get(cmd, val.get('any', None))
        return val

    @staticmethod
    def _joinCmdNameWithAliases(cmd):
        if not cmd.aliases:
            return cmd.name
        return cmd.name + '|' + '|'.join(cmd.aliases)

    @staticmethod
    def _makeCmdUsageText(progName, cmd):
        template = "%s " + cmd.usageTextTempl
        return template % (progName, CmdLineParser._joinCmdNameWithAliases(cmd))

    def _showHelp(self, cmdHelps, topic):
        if topic == 'overview':
            self._parser.print_help()
            return True

        _topic = self._cmdNameMap.get(topic, None)
        if _topic:
            _topic = _topic.name

        if _topic is None or _topic not in cmdHelps:
            log.error("Unknown command/topic to show help: '%s'" % topic)
            return False

        print(cmdHelps[_topic]['help'])
        return True

    def _addCmdPosArgs(self, target, cmd):
        posargs = [x for x in config.posargs if cmd.name in x.commands]
        for arg in posargs:
            kwargs = _AutoDict()
            for k, v in arg.items():
                if v is None or k in PosArg.NOTARGPARSE_FIELDS:
                    continue
                kwargs[k] = v
            target.add_argument(arg.name, **kwargs)

    def _addOptions(self, target, cmd = None):
        if cmd is None:
            # get only global options
            options = self._globalOptions
        else:
            def isvalid(opt):
                if opt.isglobal:
                    return False
                return cmd.name in opt.commands
            options = [x for x in config.options if isvalid(x)]

        for opt in options:
            kwargs = _AutoDict()
            for k, v in opt.items():
                if v is None or k in Option.NOTARGPARSE_FIELDS:
                    continue
                kwargs[k] = v

            if 'runcmd' in opt:
                kwargs.action = "store_true"
                if 'help' in opt:
                    kwargs.help = opt.help
                else:
                    kwargs.help = "run command '%s' before command '%s'" \
                                  % (opt.runcmd, cmd.name)
            else:
                default = self._getOptionDefault(opt, cmd)
                if default is not None:
                    kwargs['default'] = default
                    kwargs['help'] += ' [default: %r]' % kwargs['default']

            target.add_argument(*opt.names, **kwargs)

    def _fillCmdInfo(self, parsedArgs, notparsed):
        args = _AutoDict(vars(parsedArgs))
        for opt in self._globalOptions:
            if 'runcmd' in opt:
                optName = opt.names[-1].replace('-', '', 2)
                args.pop(optName, None)
        cmd = self._cmdNameMap[args.pop('command')]
        self._command = ParsedCommand(
            name = cmd.name,
            args = args,
            notparsed = notparsed,
            orig = self._origArgs,
        )

    def _postProcess(self):
        args = self._command.args
        path = args.get('destdir')
        if path:
            args['destdir'] = unfoldPath(CWD, path)

    def _fillWafCmdLine(self):
        # NOTE: The option/command 'distclean'/'cleanall' is handled in special way

        cmdName = self._command.name
        cmdline = [cmdName]

        # self._command.args is AutoDict and it means that it'll create
        # nonexistent keys inside, so we need to make a copy
        options = _AutoDict(self._command.args)

        cmdConfig = next(x for x in config.commands if x.name == cmdName)

        if cmdConfig.cmdBefore:
            cmdline.insert(0, cmdConfig.cmdBefore)

        if cmdName == 'build':
            runTests = options.get('runTests')
            if runTests is not None and runTests != 'none':
                cmdline.append('test')

        for opt in ('configure', 'clean', 'cleanall', 'distclean'):
            if options.get(opt):
                cmdline.insert(0, opt)
        for opt in ('jobs', 'destdir', 'prefix', 'bindir', 'libdir'):
            val = options.get(opt)
            if val:
                cmdline.append('--%s=%s' % (opt, str(val)))
        if 'color' in options:
            val = options.color
            if isinstance(val, bool):
                val = 'yes' if val else 'no'
            cmdline.append('--color=%s' % val)

        if options.progress:
            cmdline.append('--progress')
        if options.verbose:
            cmdline.append('-' + options.verbose * 'v')

        self._wafCmdLine = cmdline

    def parse(self, args = None, defaultCmd = 'help'):
        """ Parse command line args """

        if args is None:
            args = sys.argv[1:]

        self._origArgs = args
        _args = []
        notparsed = []
        for i, arg in enumerate(args):
            if arg == '--':
                notparsed = args[i+1:]
                break
            _args.append(arg)
        args = _args

        globalOpts = self._globalOptions
        if args:
            for opt in globalOpts:
                runcmd = opt.get('runcmd')
                # check that global option is 'help' or has 'runcmd'
                assert runcmd or opt.action == 'help'
                if runcmd and args[0] in opt.names:
                    # convert option into corresponding command
                    args[0] = runcmd
                    break

        # simple hack to set default command
        if not args or args[0].startswith('-'):
            # don't use global options for default command
            forbiddenNames = [y for x in globalOpts for y in x.names]
            if not any(x in forbiddenNames for x in args):
                args.insert(0, defaultCmd)
                self._origArgs.insert(0, defaultCmd)

        # parse
        parsedArgs = self._parser.parse_args(args)
        cmd = self._cmdNameMap[parsedArgs.command]

        if cmd.name == 'help':
            self._fillCmdInfo(parsedArgs, notparsed)
            sys.exit(not self._showHelp(self._commandHelps, parsedArgs.topic))

        self._fillCmdInfo(parsedArgs, notparsed)
        self._postProcess()
        self._fillWafCmdLine()
        return self._command

    @property
    def command(self):
        """ current command after last parsing of command line"""
        return self._command

    @property
    def wafCmdLine(self):
        """
        current command line args for WAF command after last
        parsing of command line
        """
        return self._wafCmdLine

def parseAll(args, noBuildConf = True, defaults = None):
    """
    Parse all command line args with CmdLineParser and save selected
    command as object of ParsedCommand in global var 'selected' of this module.
    Returns selected command as object of ParsedCommand and parser.wafCmdLine
    """

    # simple hack for default behavior if command is not defined
    defaultCmd = 'help' if noBuildConf else 'build'

    if defaults is None:
        defaults = {}
    parser = CmdLineParser(APPNAME, defaults)
    cmd = parser.parse(args[1:], defaultCmd)

    return cmd, parser.wafCmdLine
