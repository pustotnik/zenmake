# coding=utf-8
#

"""
 Copyright (c) 2019 Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.

 Some portions derived from Thomas Nagy's Waf code
 Waf is Copyright (c) 2005-2019 Thomas Nagy

"""

import os
import sys
import re
import shutil
import traceback
import inspect
from collections import deque

from waflib import Task, Options, Runner
from waflib.Utils import SIG_NIL, O755
from waflib.Context import create_context as createContext
from waflib.Configure import ConfigurationContext as WafConfContext, conf
from waflib.Configure import find_program as wafFindProgram
from waflib import Errors as waferror
from waflib.Tools.c_config import DEFKEYS, SNIP_EMPTY_PROGRAM, build_fun as defaultCfgBuildFunc
from zm.constants import CONFTEST_DIR_PREFIX
from zm.pyutils import maptype, stringtype
from zm.autodict import AutoDict as _AutoDict
from zm import utils, log, error, cli
from zm.pathutils import getNativePath, unfoldPath
from zm.features import ToolchainVars
from zm.waf import ccroot

joinpath = os.path.join

_RE_PKGCONFIG_PKGS = re.compile(r"(\S+)(\s*(?:[<>]|=|[<>]\s*=)\s*[^\s<>=]+)?")
_RE_FINDFILE_VAR = re.compile(r"[-.]")

CONFTEST_HASH_USED_ENV_KEYS = set(
    ('DEST_BINFMT', 'DEST_CPU', 'DEST_OS')
)
for _var in ToolchainVars.allCfgVarsToSetToolchain():
    CONFTEST_HASH_USED_ENV_KEYS.add(_var)
    CONFTEST_HASH_USED_ENV_KEYS.add('%s_VERSION' % _var)
    CONFTEST_HASH_USED_ENV_KEYS.add('%s_NAME' % _var)

CONFTEST_HASH_IGNORED_FUNC_ARGS = frozenset(
    ('mandatory', 'msg', 'okmsg', 'errmsg', 'id', 'before', 'after')
)

_cache = {}

def cfgmandatory(func):
    """
    Handle a parameter named 'mandatory' to disable the configuration errors
    """

    def decorator(*args, **kwargs):
        mandatory = kwargs.pop('mandatory', True)
        try:
            return func(*args, **kwargs)
        except waferror.ConfigurationError:
            if mandatory:
                raise

    return decorator

@conf
def find_program(self, filename, **kwargs):
    """
    It's replacement for waflib.Configure.find_program to provide some
    additional abiliies.
    """
    # pylint: disable = invalid-name

    filename = utils.toListSimple(filename)

    # simple caching
    useCache = all(x not in kwargs for x in ('environ', 'exts', 'value'))
    if useCache:
        cache = _cache.setdefault('find-program', {})
        pathList = kwargs.get('path_list')
        pathList = tuple(pathList) if pathList else None
        filenameKey = (tuple(filename), kwargs.get('interpreter'), pathList)
        result = cache.get(filenameKey)
        if result is not None:
            kwargs['value'] = result
            kwargs['endmsg-postfix'] = ' (cached)'

    result = wafFindProgram(self, filename, **kwargs)

    if useCache:
        cache[filenameKey] = result
    return result

def _applyFindProgramResults(cfgCtx, args):
    cfgCtx.env[args['var']] = args['$result']

def _applyFindFileResults(cfgCtx, args):
    cfgCtx.env[args['var']] = args['$result']

def _getDefaultFindFileVar(filename):
    return _RE_FINDFILE_VAR.sub('_', filename.upper())

def _findProgram(params, filenames, checkArgs):

    filenames = utils.toList(filenames)

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    checkArgs = checkArgs.copy()
    if 'path_list' not in checkArgs:
        checkArgs['path_list'] = utils.toList(checkArgs.pop('paths', []))

    if not checkArgs.get('var'):
        checkArgs['var'] = _getDefaultFindFileVar(filenames[0])

    result = cfgCtx.find_program(filenames, **checkArgs)

    if result:
        result = ' '.join(result)
        storedActions = taskParams['$stored-actions']
        checkArgs['$result'] = cfgCtx.env[checkArgs['var']]
        storedActions.append({'type' : 'find-program', 'data' : checkArgs })

    return result

def _makeRunBuildBldCtx(ctx, args, topdir, bdir):

    bld = createContext('build', top_dir = topdir, out_dir = bdir)

    # avoid unnecessary directories
    bld.buildWorkDirName = bld.variant = ''

    bld.init_dirs()
    bld.progress_bar = 0
    bld.targets = '*'

    bld.logger = ctx.logger
    # for TaskGen __init__
    bld.env = args['env']

    # for function 'build_fun' only
    bld.kw = { k:v for k,v in args.items() if k[0] != '$' }
    bld.conf = ctx # it's used for bld.conf.to_log

    return bld

def _runCheckBuild(self, checkArgs):
    """
    It's alternative implementation for the waflib.Configure.run_build.
    This method must be thread safe.
    """

    cfgCtx = self if isinstance(self, WafConfContext) else self.cfgCtx

    # WARN:
    # Any method from cfgCtx that is used here must be thread safe

    # this function can not be called from conf.multicheck
    assert getattr(self, 'multicheck_task', None) is None

    checkHash = checkArgs['$conf-test-hash']
    checkCache = cfgCtx.getConfCache()['config-actions'][checkHash]

    retval = checkCache['retval']
    if retval is not None:
        retArgs = checkArgs.get('ret-args', checkArgs)
        retArgs['endmsg-postfix'] = ' (cached)'

        if isinstance(retval, stringtype) and retval.startswith('Conf test failed'):
            self.fatal(retval)
        return retval

    checkId = str(checkCache['id'])
    if '$parallel-id' in checkArgs:
        checkId = '%s.%s' % (checkId, checkArgs['$parallel-id'])

    topdir = cfgCtx.bldnode.abspath() + os.sep
    topdir += '%s%s' % (CONFTEST_DIR_PREFIX, checkId)

    if os.path.exists(topdir):
        shutil.rmtree(topdir)

    try:
        os.makedirs(topdir)
    except OSError:
        pass

    try:
        os.stat(topdir)
    except OSError:
        self.fatal('cannot use the configuration test folder %r' % topdir)

    bdir = joinpath(topdir, 'b')
    if not os.path.exists(bdir):
        os.makedirs(bdir)

    bld = _makeRunBuildBldCtx(self, checkArgs, topdir, bdir)

    # Run function 'build_fun' (see waflib.Tools.c_config.build_fun)
    # It creates task generator for conf test.
    checkArgs['build_fun'](bld)
    retval = -1

    try:
        try:
            bld.compile()
        except waferror.WafError:
            # TODO: add more info?
            tsk = bld.producer.error[0]
            errDetails = "\n[CODE]\n%s" % bld.kw['code']
            errDetails += "\n[LAST COMMAND]\n%s" % tsk.last_cmd
            retval = 'Conf test failed: %s' % errDetails

            self.fatal(retval)
        else:
            retval = getattr(bld, 'retval', 0)
    finally:
        shutil.rmtree(topdir)
        checkCache['retval'] = retval

    return retval

def _preCheck(cfgCtx, args):
    """
    It's replacement for waflib.Tools.c_config.validate_c to provide good
    thead safety. This method is mostly compatible with validate_c.
    """
    # pylint: disable = too-many-branches, too-many-statements

    args.setdefault('build_fun', defaultCfgBuildFunc)

    # for defaultCfgBuildFunc
    args.setdefault('env', cfgCtx.env.derive())

    # read only
    env = cfgCtx.env

    if 'compiler' not in args and 'features' not in args:
        if env.CXX_NAME and Task.classes.get('cxx'):
            if not env.CXX:
                cfgCtx.fatal('a c++ compiler is required')
            args['compiler'] = 'cxx'
        else:
            if not env.CC:
                cfgCtx.fatal('a c compiler is required')
            args['compiler'] = 'c'

    features = utils.toListSimple(args.get('features', []))

    if 'compile_mode' not in args:
        if 'cxx' in features or args.get('compiler') == 'cxx':
            args['compile_mode'] = 'cxx'
        else:
            args['compile_mode'] = 'c'

    compileMode = args['compile_mode']

    args.setdefault('type', 'cprogram')

    if not features:
        features = [compileMode]
        if not 'header_name' in args or args.get('link_header_test', True):
            features.append(args['type'])

    args['features'] = features

    if 'compile_filename' not in args:
        args['compile_filename'] = 'test.c' + ((compileMode == 'cxx') and 'pp' or '')

    if 'header_name' in args:
        args.setdefault('msg', 'Checking for header %s' % args['header_name'])

        headers = utils.toListSimple(args['header_name'])
        assert len(headers) > 0, 'list of headers in header_name is empty'

        args['code'] = ''.join(['#include <%s>\n' % x for x in headers])
        args['code'] += SNIP_EMPTY_PROGRAM
        args.setdefault('uselib_store', headers[0].upper())
        if 'define_name' not in args:
            args['define_name'] = cfgCtx.have_define(headers[0])

    lib = args.get('lib')
    if lib is not None:
        args.setdefault('msg', 'Checking for library %s' % lib)
        args.setdefault('uselib_store', lib.upper())

    stlib = args.get('stlib')
    if stlib is not None:
        args.setdefault('msg', 'Checking for static library %s' % stlib)
        args.setdefault('uselib_store', stlib.upper())

    fragment = args.get('fragment')
    if fragment is not None:
        args['code'] = fragment
        args.setdefault('msg', 'Checking for code snippet')
        args.setdefault('errmsg', 'no')

    flags = (('cxxflags','compiler'), ('cflags','compiler'), ('linkflags','linker'))
    for flagsname, flagstype in flags:
        if flagsname in args:
            args.setdefault('msg', 'Checking for %s flags %s' % (flagstype, args[flagsname]))
            args.setdefault('errmsg', 'no')

    args.setdefault('execute', False)
    if args['execute']:
        args['features'].append('test_exec')
        args['chmod'] = O755

    args.setdefault('errmsg', 'not found')
    args.setdefault('okmsg', 'yes')
    args.setdefault('code', SNIP_EMPTY_PROGRAM)
    args.setdefault('success', None)

    # we don't undefine 'define_name' how it does c_config.validate_c
    assert 'msg' in args

def _getCheckSuccess(args):

    if args['execute']:
        success = 0
        defineReturn = args.get('define_ret')
        if args['success'] is not None:
            success = args['success'] if defineReturn else (args['success'] == 0)
    else:
        success = (args['success'] == 0)

    return success

def _applyCheckResults(cfgCtx, args):

    success = args['success']
    execute = args['execute']
    defineReturn = args.get('define_ret')

    defineName = args.get('define_name')
    if defineName:
        # ZenMake doesn't support adding to DEFINES_* env var here
        assert args.get('global_define', 1)

        comment = args.get('comment', '')
        if execute and defineReturn and isinstance(success, stringtype):
            cfgCtx.define(defineName, success, quote = args.get('quote', 1),
                          comment = comment)
        else:
            cfgCtx.define_cond(defineName, success, comment = comment)

        # define conf.env.HAVE_X to 1 - only for compatibility with Waf
        if args.get('add_have_to_env', 1):
            uselibVar  = args.get('uselib_store')
            if uselibVar:
                cfgCtx.env[cfgCtx.have_define(uselibVar)] = 1
            else:
                val = success if execute and defineReturn else int(success)
                cfgCtx.env[defineName] = val

    if success and 'uselib_store' in args:
        _vars = set()
        for feature in args['features']:
            _vars |= ccroot.USELIB_VARS.get(feature, set())

        uselibVar  = args['uselib_store']
        for var in _vars:
            val = args.get(var.lower())
            if val is not None:
                cfgCtx.env.append_value(var + '_' + uselibVar, val)

@conf
def check(self, *_, **kwargs):
    """
    It's alternative version of the waflib.Tools.c_config.check.
    Original 'check' from waf doesn't provide good thread
    safity and sometimes it leads to problems with defines.
    """

    _preCheck(self, kwargs)

    self.startMsg(kwargs['msg'], **kwargs)
    result = None
    try:
        # _runCheckBuild is supposedly thread safe
        result = _runCheckBuild(self, kwargs)
    except waferror.ConfigurationError:
        self.endMsg(kwargs['errmsg'], 'YELLOW', **kwargs)
        if log.verbose() > 1:
            raise
        self.fatal('The configuration failed')
    else:
        kwargs['success'] = result

    kwargs['success'] = result = _getCheckSuccess(kwargs)
    savedArgs = kwargs.get('saved-result-args')
    if savedArgs is not None:
        savedArgs.append({'type' : 'check', 'data' : kwargs })

    if kwargs.get('apply-results', True):
        _applyCheckResults(self, kwargs)

    if not result:
        self.endMsg(kwargs['errmsg'], 'YELLOW', **kwargs)
        self.fatal('The configuration failed %r' % result)
    else:
        self.endMsg(kwargs['okmsg'], **kwargs)
    return result

@conf
def runPyFuncAsAction(self, **kwargs):
    """
    Run python function as an action
    """

    # pylint: disable = broad-except

    func = kwargs['func']
    args = kwargs['args']

    self.startMsg(kwargs['msg'])

    withException = False
    try:
        if args:
            result = func(**args)
        else:
            result = func()
    except Exception:
        result = False
        withException = True

    if result:
        self.endMsg('yes')
        return

    self.endMsg('no', color = 'YELLOW')

    msg = "\nConfig function %r failed: " % func.__name__

    if withException:
        excInfo = sys.exc_info()
        stack = traceback.extract_tb(excInfo[2])[-1::]
        msg += "\n%s: %s\n" % (excInfo[0].__name__, excInfo[1])
        msg += "".join(traceback.format_list(stack))
    else:
        msg += "function returned %s" % str(result)

    if log.verbose() > 1:
        # save to log and raise exception
        self.fatal(msg)

    try:
        # save to log but don't allow exception
        self.fatal(msg)
    except waferror.ConfigurationError:
        pass

    self.fatal('The configuration failed')

def callPyFunc(actionArgs, params):
    """ Make or prepare python function as an action """

    cfgCtx    = params['cfgCtx']
    buildtype = params['buildtype']
    taskName  = params['taskName']

    actionArgs = actionArgs.copy()

    func = actionArgs['func']
    argsSpec = inspect.getfullargspec(func)
    noFuncArgs = not any(argsSpec[0:3])
    args = { 'taskname' : taskName, 'buildtype' : buildtype }

    actionArgs['args'] = None if noFuncArgs else args
    actionArgs['msg'] = 'Function %r' % func.__name__

    parallelActions = params.get('parallel-actions', None)

    if parallelActions is not None:
        # actionArgs is shared so it can be changed later
        actionArgs['$func-name'] = 'runPyFuncAsAction'
        parallelActions.append(actionArgs)
    else:
        cfgCtx.runPyFuncAsAction(**actionArgs)

def findProgram(checkArgs, params):
    """ Find a program """

    names = checkArgs.pop('names', [])
    if not names:
        # do nothing
        return

    checkArgs['path_list'] = utils.toList(checkArgs.pop('paths', []))

    _findProgram(params, names, checkArgs)

def findFile(checkArgs, params):
    """ Find a file """

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    names = utils.toList(checkArgs.get('names', []))
    if not names:
        # do nothing
        return

    names = [getNativePath(x) for x in names]
    checkArgs['names'] = names

    paths = utils.toList(checkArgs.get('paths', []))
    if not paths:
        paths = ['.']
    paths = [getNativePath(x) for x in paths]
    checkArgs['paths'] = paths

    var = checkArgs.get('var')
    if not var:
        var = _getDefaultFindFileVar(names[0])
    checkArgs['var'] = var

    checkArgs['startdir'] = params['bconf'].confPaths.startdir

    @cfgmandatory
    def _find(cfgCtx, **kwargs):
        msgArgs = {}

        names = kwargs['names']
        paths = kwargs['paths']
        var = kwargs['var']
        startdir = checkArgs['startdir']

        result = None
        for name in names:
            for path in paths:
                path = unfoldPath(startdir, joinpath(path, name))
                if os.path.isfile(path) or os.path.islink(path):
                    result = path
                    break

        msg = ', '.join(names)
        msgArgs['result'] = result if result else False
        cfgCtx.msg('Checking for file %r' % msg, **msgArgs)
        cfgCtx.to_log('find file=%r paths=%r var=%r -> %r' % (names, paths, var, result))

        if result:
            cfgCtx.env[var] = result
        else:
            msg = 'Could not find'
            msg += ' %r' % (names if len(names) > 1 else names[0])
            cfgCtx.fatal(msg)

        return result

    result = _find(cfgCtx, **checkArgs)

    if result:
        cfgCtx.env[var] = result
        storedActions = taskParams['$stored-actions']
        checkArgs['var'] = var
        checkArgs['$result'] = result
        storedActions.append({'type' : 'find-file', 'data' : checkArgs })

def _handleLoadedActionsCache(cache):
    """
    Handle loaded cache data for config actions.
    """

    cacheCfgActionResults = False
    if cli.selected:
        # cli.selected can be None in unit tests
        cacheCfgActionResults = cli.selected.args.get('cacheCfgActionResults')

    if 'config-actions' not in cache:
        cache['config-actions'] = {}
    actions = cache['config-actions']

    if not cacheCfgActionResults:
        # reset all but not 'id'
        for v in actions.values():
            if isinstance(v, maptype):
                _new = { 'id' : v['id']}
                v.clear()
                v.update(_new)

    return actions

def _getConfActionCache(cfgCtx, actionHash):
    """
    Get conf action cache by hash
    """

    cache = cfgCtx.getConfCache()
    actions = cache['config-actions']

    if actionHash not in actions:
        lastId = actions.get('last-id', 0)
        actions['last-id'] = currentId = lastId + 1
        actions[actionHash] = {}
        actions[actionHash]['id'] = currentId

    return actions[actionHash]

def _calcConfCheckHexHash(checkArgs, params):

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    hashVals = {}
    for k, v in checkArgs.items():
        if k in CONFTEST_HASH_IGNORED_FUNC_ARGS or k[0] == '$':
            continue
        hashVals[k] = v
    # just in case
    hashVals['toolchain'] = utils.toList(taskParams.get('toolchain', []))

    buff = [ '%s: %s' % (k, str(hashVals[k])) for k in sorted(hashVals.keys()) ]

    env = cfgCtx.env
    envStr = ''
    for k in sorted(env.keys()):
        if k not in CONFTEST_HASH_USED_ENV_KEYS:
            # these keys are not significant for hash but can make cache misses
            continue
        val = env[k]
        envStr += '%r %r ' % (k, val)
    buff.append('%s: %s' % ('env', envStr))

    return utils.hexOfStr(utils.hashObj(buff))

def _checkWithBuild(checkArgs, params):
    """
    Check it with building of some code.
    It's general function for many checks.
    """

    cfgCtx = params['cfgCtx']
    taskParams = params['taskParams']

    # _checkWithBuild is used in loops so it's needed to save checkArgs
    # without changes
    checkArgs = checkArgs.copy()

    hexHash = _calcConfCheckHexHash(checkArgs, params)
    checkCache = _getConfActionCache(cfgCtx, hexHash)
    if 'retval' not in checkCache:
        # to use it without lock in threads we need to insert this key
        checkCache['retval'] = None
    checkArgs['$conf-test-hash'] = hexHash

    defname = checkArgs.pop('defname', None)
    if defname:
        checkArgs['define_name'] = defname

    codeType = checkArgs.pop('code-type', None)
    if codeType:
        checkArgs['compiler'] = checkArgs['compile_mode'] = codeType
        checkArgs['type'] = '%sprogram' % codeType

    compileFilename = checkArgs.pop('compile-filename', None)
    if compileFilename:
        checkArgs['compile_filename'] = compileFilename

    defines = checkArgs.pop('defines', None)
    if defines:
        checkArgs['defines'] = utils.toList(defines)

    libpath = taskParams.get('libpath', None)
    if libpath:
        checkArgs['libpath'] = libpath

    includes = taskParams.get('includes', None)
    if includes:
        checkArgs['includes'] = includes

    # don't add defname into env in the form self.env.defname
    # ZenMake doesn't need it
    checkArgs['add_have_to_env'] = 0

    parallelActions = params.get('parallel-actions', None)

    if parallelActions is not None:
        # checkArgs is shared so it can be changed later
        checkArgs['$func-name'] = 'check'
        parallelActions.append(checkArgs)
    else:
        checkArgs['saved-result-args'] = taskParams['$stored-actions']
        cfgCtx.check(**checkArgs)

def checkLibs(checkArgs, params):
    """ Check shared libraries """

    autodefine = checkArgs.pop('autodefine', False)

    libs = []
    if checkArgs.pop('fromtask', True):
        taskParams = params['taskParams']
        libs.extend(utils.toList(taskParams.get('libs', [])))
        libs.extend(utils.toList(taskParams.get('lib', [])))
    libs.extend(utils.toList(checkArgs.pop('names', [])))
    libs = utils.uniqueListWithOrder(libs)

    for lib in libs:
        _checkArgs = checkArgs.copy()
        _checkArgs['msg'] = 'Checking for library %s' % lib
        _checkArgs['lib'] = lib
        if autodefine and 'define_name' not in _checkArgs:
            _checkArgs['define_name'] = 'HAVE_LIB_' + lib.upper()
        _checkWithBuild(_checkArgs, params)

def checkHeaders(checkArgs, params):
    """ Check headers """

    headers = utils.toList(checkArgs.pop('names', []))
    for header in headers:
        checkArgs['msg'] = 'Checking for header %s' % header
        checkArgs['header_name'] = header
        _checkWithBuild(checkArgs, params)

def checkCode(checkArgs, params):
    """ Check code snippet """

    cfgCtx = params['cfgCtx']
    taskName = params['taskName']

    msg = 'Checking code snippet'
    label = checkArgs.pop('label', None)
    if label is not None:
        msg += " %r" % label

    checkArgs['msg'] = msg

    text = checkArgs.pop('text', None)
    file = checkArgs.pop('file', None)

    if all((not text, not file)):
        msg = "Neither 'text' nor 'file' set in a config action"
        msg += " 'check-code' for task %r" % taskName
        cfgCtx.fatal(msg)

    if text:
        checkArgs['fragment'] = text
        _checkWithBuild(checkArgs, params)

    if file:
        startdir = params['bconf'].confPaths.startdir
        file = getNativePath(file)
        path = joinpath(startdir, file)
        if not os.path.isfile(path):
            msg = "Error in declaration of a config action "
            msg += "'check-code' for task %r:" % taskName
            msg += "\nFile %r doesn't exist" % file
            if not os.path.abspath(file):
                msg += " in the directory %r" % startdir
            cfgCtx.fatal(msg)

        cfgCtx.monitFiles.append(path)

        with open(path, 'r') as file:
            text = file.read()

        checkArgs['fragment'] = text
        _checkWithBuild(checkArgs, params)

def _parsePkgConfigPackages(packages, confpath):

    result = []

    packageGroups = _RE_PKGCONFIG_PKGS.findall(packages)
    # remove all whitespaces
    packageGroups = [ ( x[0], ''.join(x[1].split()) ) for x in packageGroups]

    def raiseInvalidPackages(packages, confpath):
        msg = "The value %r is invalid for the parameter 'packages'" % packages
        msg += " in config action 'pkgconfig'"
        raise error.ZenMakeConfError(msg, confpath = confpath)

    pkgInfo = _AutoDict()
    pkgSeen = set()
    for name, verline in packageGroups:
        if any(x in name for x in ('<', '>', '=')):
            raiseInvalidPackages(packages, confpath)

        pkgItem = pkgInfo[name]
        pkgItem.name = name

        pkgItem.setdefault('uselib', name)
        pkgItem.setdefault('cmdline', [])
        cmdarg = name

        if verline:
            if len(verline) < 2 or not any(verline[0] == x for x in ('<', '>', '=')):
                raiseInvalidPackages(packages, confpath)
            index = 1
            if verline[1] == '=':
                index = 2
            cmdarg += " %s %s" % (verline[0:index], verline[index:])

            _verline = verline.replace('<', 'l').replace('>', 'g').replace('=', 'e')
            pkgItem.uselib += '_%s' % _verline

        pkgItem.cmdline.append(cmdarg)

        if name not in pkgSeen:
            result.append(pkgItem)
            pkgSeen.add(name)

    for item in result:
        item.uselib = utils.normalizeForDefine(item.uselib)

    return result

def _applyToolConfigResults(cfgCtx, args):

    taskParams = args['$task-params']

    parseFlags = args.get('parse-flags', False)
    if parseFlags:
        output = args['output']
        uselib = args['uselib']
        cfgCtx.parse_flags(output, uselib, cfgCtx.env, args['static'])

        # add to task
        taskUselib = taskParams.setdefault('uselib', [])
        taskUselib.append(uselib)

    defvar = args.get('defname')
    if defvar:
        defval = args.get('defval', 1)
        defquote = args.get('defquote', True)
        cfgCtx.define(defvar, defval, quote = defquote)

    substvar = args.get('substvar')
    if substvar:
        substval = args.get('substval', '')
        taskSubstvars = taskParams.setdefault('substvars', {})
        taskSubstvars[substvar] = substval

    storeArgs = args.get('store-args', False)
    if storeArgs:
        args = args.copy()
        args.pop('$task-params')
        args.pop('store-args')
        storedActions = taskParams['$stored-actions']
        storedActions.append({'type' : 'tool-config', 'data' : args })

@cfgmandatory
def _runToolConfig(cfgCtx, taskParams, **kwargs):
    """
    Run ``pkg-config`` or other ``-config`` applications and parse result
    """

    cmd = [kwargs['runpath']]
    cmd += kwargs['cmd-args']

    cfgCtx.startMsg(kwargs['msg'])
    try:

        cmdEnv = cfgCtx.env.env or None
        output = cfgCtx.cmd_and_log(cmd, env = cmdEnv)

        kwargs.update({
            '$task-params' : taskParams, 'output' : output, 'store-args' : True,
        })
        _applyToolConfigResults(cfgCtx, kwargs)

    except waferror.WafError as ex:
        cfgCtx.endMsg(kwargs['errmsg'], color = 'YELLOW')
        if log.verbose() > 1:
            cfgCtx.to_log('Command failure: %s' % ex)
        cfgCtx.fatal('The configuration failed')
    else:
        okmsg = kwargs.get('okmsg')
        if okmsg is not None:
            cfgCtx.endMsg(kwargs['okmsg'])

    return output

def _doPkgConfigForOne(cfgCtx, pkgInfo, actionArgs, taskParams):

    pkgname = pkgInfo.name

    defnames = actionArgs['defnames']
    if defnames is not None:
        defnames = {} if defnames is True else defnames
        defnames = defnames.get(pkgname, {})

    def setDefine(kind, value):
        if defnames is None:
            return

        defvar = defnames.get(kind, True)
        if defvar is True:
            if kind == 'have':
                defvar = cfgCtx.have_define(pkgname)
            else:
                assert kind == 'version'
                defvar = '%s_VERSION' % utils.normalizeForDefine(pkgname)

        if defvar:
            kwargs = {
                '$task-params' : taskParams, 'store-args' : True,
                'defname' : defvar, 'defval' : value,
                'defquote' : (kind == 'version'),
            }
            _applyToolConfigResults(cfgCtx, kwargs)

    getPkgVer = actionArgs.get('pkg-version', False)
    if getPkgVer:
        kwargs = actionArgs.copy()
        kwargs['msg'] = 'Getting version for %r' % pkgname
        kwargs['cmd-args'] = ['--modversion', pkgname]
        kwargs.pop('okmsg', None)
        version = _runToolConfig(cfgCtx, taskParams, **kwargs)
        if version is not None:
            version = version.strip()
            # set *_VERSION define
            setDefine('version', version)
            cfgCtx.endMsg(version)

        if not actionArgs['libs'] and not actionArgs['cflags']:
            setDefine('have', 1)
            return

    # cmd line args
    cmdArgs = ['--%s' % x for x in ('libs', 'cflags', 'static') if actionArgs[x]]

    for k, v in actionArgs.get('def-pkg-vars', {}).items():
        cmdArgs.append('--define-variable=%s=%s' % (k, v))

    cmdArgs += pkgInfo.cmdline
    actionArgs['cmd-args'] = cmdArgs

    actionArgs['uselib'] = pkgInfo.uselib
    actionArgs['parse-flags'] = True

    pkgline = "%r" % pkgname
    if pkgInfo.cmdline[0] != pkgname:
        nameLen = len(pkgname)
        verline = ' and '.join(x[nameLen + 1: ] for x in pkgInfo.cmdline)
        pkgline += ' (%s)' % verline

    actionArgs['msg'] = 'Checking for %s' % pkgline

    # run
    output = _runToolConfig(cfgCtx, taskParams, **actionArgs)
    if output is None: # when mandatory == False
        return

    # set HAVE_* define
    setDefine('have', 1)

def _getToolConfigPath(actionArgs, params):

    cfgCtx = params['cfgCtx']
    toolname = actionArgs['toolname']

    toolEnvVar = _getDefaultFindFileVar(toolname)
    toolPath = cfgCtx.env[toolEnvVar]
    if not toolPath:
        toolpaths = actionArgs.get('toolpaths', [])
        mandatory = actionArgs.get('mandatory', True)
        kwargs = { 'mandatory' : mandatory, 'paths' : toolpaths, 'var' : toolEnvVar }
        toolPath = _findProgram(params, toolname, kwargs)
    else:
        toolPath = toolPath[0]

    return toolPath

def doPkgConfig(actionArgs, params):
    """
    Do pkg-config
    """

    cfgCtx     = params['cfgCtx']
    bconf      = params['bconf']
    taskParams = params['taskParams']

    toolname = actionArgs.setdefault('toolname', 'pkg-config')

    packages = actionArgs.get('packages')
    if not packages:
        msg = "The parameter 'packages' is empty in config action 'pkgconfig'"
        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    # get/find tool path
    actionArgs['runpath'] = _getToolConfigPath(actionArgs, params)

    actionArgs.setdefault('libs', True)
    actionArgs.setdefault('cflags', True)
    actionArgs.setdefault('static', False)

    actionArgs['okmsg'] = 'yes'
    actionArgs['errmsg'] = 'not found'

    if 'tool-atleast-version' in actionArgs:
        ver = actionArgs['tool-atleast-version']
        actionArgs['msg'] = 'Checking for %s version >= %r' % (toolname, ver)
        actionArgs['cmd-args'] = ['--atleast-pkgconfig-version=%s' % ver]
        _runToolConfig(cfgCtx, taskParams, **actionArgs)

    defnames = actionArgs.setdefault('defnames', True)
    if defnames is False:
        actionArgs['defnames'] = None

    pkgItems = _parsePkgConfigPackages(packages, bconf.path)
    for pkgInfo in pkgItems:
        _doPkgConfigForOne(cfgCtx, pkgInfo, actionArgs, taskParams)

def doToolConfig(actionArgs, params):
    """
    Do *-config like sdl-config, sdl2-config, mpicc, etc.
    """

    cfgCtx     = params['cfgCtx']
    bconf      = params['bconf']
    taskParams = params['taskParams']

    toolname = actionArgs.get('toolname')

    if not toolname:
        msg = "The parameter 'toolname' is empty in config action 'toolconfig'"
        raise error.ZenMakeConfError(msg, confpath = bconf.path)

    actionArgs['cmd-args'] = utils.toList(actionArgs.pop('args', '--cflags --libs'))

    # get/find tool path
    actionArgs['runpath'] = _getToolConfigPath(actionArgs, params)

    uselib = toolname
    if toolname.endswith('-config'):
        uselib = toolname[:len(toolname)-len('-config')]
    uselib = utils.normalizeForDefine(uselib)

    actionArgs['uselib'] = uselib

    parseAs = actionArgs.pop('parse-as', 'flags-libs')
    actionArgs['parse-flags'] = (parseAs == 'flags-libs')
    actionArgs.setdefault('static', False)

    actionArgs.setdefault('msg', 'Checking for %s' % uselib)
    actionArgs['okmsg'] = 'yes'
    actionArgs['errmsg'] = 'not found'

    # run
    output = _runToolConfig(cfgCtx, taskParams, **actionArgs)
    if output is None: # when mandatory == False
        return

    defvar = actionArgs.get('defname')
    if not defvar and parseAs == 'flags-libs':
        defvar = 'HAVE_%s' % uselib

    output = output.strip()
    if defvar:
        defval = 1
        quoteDefVal = False
        if parseAs == 'entire':
            defval = output
            quoteDefVal = True

        kwargs = {
            '$task-params' : taskParams, 'store-args' : True,
            'defname' : defvar, 'defval' : defval, 'defquote' : quoteDefVal,
        }
        _applyToolConfigResults(cfgCtx, kwargs)

    substvar = actionArgs.get('var')
    if substvar and parseAs == 'entire':
        kwargs = {
            '$task-params' : taskParams, 'store-args' : True,
            'substvar' : substvar, 'substval' : output,
        }
        _applyToolConfigResults(cfgCtx, kwargs)

def _applyWriteConfigHeaderResults(cfgCtx, args):

    if args['remove']:
        for key in cfgCtx.env[DEFKEYS]:
            cfgCtx.undefine(key)
        cfgCtx.env[DEFKEYS] = []

def writeConfigHeader(checkArgs, params):
    """ Write config header """

    buildtype  = params['buildtype']
    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']
    taskParams = params['taskParams']

    def defaultFileName():
        return utils.normalizeForFileName(taskName).lower()

    fileName = checkArgs.pop('file', None)
    if not fileName:
        fileName = '%s_%s' % (defaultFileName(), 'config.h')
    fileName = joinpath(buildtype, fileName)

    guardname = checkArgs.pop('guard', None)
    if not guardname:
        projectName = params['bconf'].projectName or ''
        guardname = utils.normalizeForDefine(projectName + '_' + fileName)
    checkArgs['guard'] = guardname

    # remove the defines after they are added
    checkArgs['remove'] = checkArgs.pop('remove-defines', True)

    # write the configuration header from the build directory
    checkArgs['top'] = True

    cfgCtx.write_config_header(fileName, **checkArgs)

    storedActions = taskParams['$stored-actions']
    storedActions.append({'type' : 'write-conf-header', 'data' : checkArgs })

class _CfgCheckTask(Task.Task):
    """
    A task that executes build configuration tests (calls conf.check).
    It's used to run conf checks in parallel.
    """

    def __init__(self, *args, **kwargs):
        Task.Task.__init__(self, *args, **kwargs)

        self.stopRunnerOnError = True
        self.conf = None
        self.bld = None
        self.logger = None
        self.call = None
        self._retArgs = {}

    def display(self):
        return ''

    def runnable_status(self):
        for task in self.run_after:
            if not task.hasrun:
                return Task.ASK_LATER
        return Task.RUN_ME

    def uid(self):
        return SIG_NIL

    def signature(self):
        return SIG_NIL

    def run(self):
        """ Run task """

        # pylint: disable = broad-except

        cfgCtx = self.conf
        topdir = cfgCtx.srcnode.abspath()
        bdir = cfgCtx.bldnode.abspath()
        bld = createContext('build', top_dir = topdir, out_dir = bdir)

        # avoid unnecessary directories
        bld.buildWorkDirName = bld.variant = ''
        # make deep copy of env to avoid any problems with threads
        bld.env = utils.deepcopyEnv(cfgCtx.env, lambda k: k[0] != '$')
        bld.init_dirs()
        bld.in_msg = 1 # suppress top-level startMsg
        bld.logger = self.logger
        bld.cfgCtx = cfgCtx

        args = self.call['args']
        func = getattr(bld, self.call['name'])

        args['saved-result-args'] = self.generator.bld.savedResultArgs
        args['apply-results'] = False
        args['ret-args'] = self._retArgs

        mandatory = args.get('mandatory', True)
        args['mandatory'] = True
        retval = 0
        try:
            func(**args)
        except waferror.WafError:
            retval = 1
        except Exception:
            retval = 1
            errmsg = traceback.format_exc()
            cfgCtx.to_log(errmsg)
            if log.verbose() > 1:
                log.error(errmsg)
        finally:
            args['mandatory'] = mandatory

        if retval != 0 and mandatory and self.stopRunnerOnError:
            # say 'stop' to runner
            self.bld.producer.stop = True

        return retval

    def process(self):

        Task.Task.process(self)

        args = self.call['args']
        if 'msg' not in args:
            return

        endMsgArgs = self._retArgs
        errmsg = args.get('errmsg', 'no')
        okmsg = args.get('okmsg', 'yes')
        with self.generator.bld.cmnLock:
            self.conf.startMsg(args['msg'])
            if self.hasrun == Task.NOT_RUN:
                self.conf.endMsg('cancelled', color = 'YELLOW', **endMsgArgs)
            elif self.hasrun != Task.SUCCESS:
                self.conf.endMsg(errmsg, color = 'YELLOW', **endMsgArgs)
            else:
                self.conf.endMsg(okmsg, color = 'GREEN', **endMsgArgs)

class _RunnerBldCtx(object):
    """
    A class that is used as BuildContext to execute conf tests in parallel
    """

    # pylint: disable = invalid-name, missing-docstring

    def __init__(self, tasks):

        # Keep running all tasks while all tasks will not be not processed
        # and self.producer.stop == False
        self.keep = True

        self.task_sigs = {}
        self.imp_sigs = {}
        self.progress_bar = 0
        self.producer = None
        self.cmnLock = utils.threading.Lock()
        # deque has fast atomic append() and popleft() operations that
        # do not require locking
        self.savedResultArgs = deque()
        self.tasks = tasks

    def total(self):
        return len(self.tasks)

    def to_log(self, *k, **kw):
        # pylint: disable = unused-argument
        return

def _applyParallelActionsDeps(tasks, bconfpath):

    idToTask = {}
    for tsk in tasks:
        args = tsk.call['args']
        if 'id' in args:
            idToTask[args['id']] = tsk

    def applyDeps(idToTask, task, before):
        tasks = task.call['args'].get('before' if before else 'after', [])
        for key in utils.toList(tasks):
            otherTask = idToTask.get(key, None)
            if not otherTask:
                msg = 'No config action named %r' % key
                raise error.ZenMakeConfError(msg, confpath = bconfpath)
            if before:
                otherTask.run_after.add(task)
            else:
                task.run_after.add(otherTask)

    # second pass to set dependencies with after/before
    for tsk in tasks:
        applyDeps(idToTask, tsk, before = True)
        applyDeps(idToTask, tsk, before = False)

    # remove 'before' and 'after' from args to avoid matching with the same
    # parameters for Waf Task.Task
    for tsk in tasks:
        args = tsk.call['args']
        args.pop('before', None)
        args.pop('after', None)

def _processParallelActionsResults(params, runnerCtx, scheduler):

    cfgCtx = params['cfgCtx']
    cfgCtx.startMsg('-> processing results')

    # apply results out of threads
    storedActions = params['taskParams']['$stored-actions']
    for resultArgs in runnerCtx.savedResultArgs:
        atype = resultArgs['type']
        if atype == 'check':
            _applyCheckResults(cfgCtx, resultArgs['data'])
        else:
            raise NotImplementedError
        storedActions.append(resultArgs)

    for tsk in scheduler.error:
        if not getattr(tsk, 'err_msg', None):
            continue
        cfgCtx.to_log(tsk.err_msg)
        cfgCtx.endMsg('fail', color = 'RED')
        msg = 'There is an error in the Waf, read config.log for more information'
        raise waferror.WafError(msg)

    tasks = runnerCtx.tasks
    okStates = (Task.SUCCESS, Task.NOT_RUN)
    failureCount = len([x for x in tasks if x.hasrun not in okStates])

    if failureCount:
        cfgCtx.endMsg('%s failed' % failureCount, color = 'YELLOW')
    else:
        cfgCtx.endMsg('all ok')

    for tsk in tasks:
        # in rare case we get "No handlers could be found for logger"
        log.freeLogger(tsk.logger)

        if tsk.hasrun not in okStates and tsk.call['args'].get('mandatory', True):
            cfgCtx.fatal('One of the actions has failed, read config.log for more information')

def _runActionsInParallelImpl(params, actionArgsList, **kwargs):
    """
    Runs configuration actions in parallel.
    Results are printed sequentially at the end.
    """

    cfgCtx = params['cfgCtx']
    bconf  = params['bconf']

    cfgCtx.startMsg('Paralleling %d actions' % len(actionArgsList))

    tasks = []
    runnerCtx = _RunnerBldCtx(tasks)

    tryall = kwargs.get('tryall', False)

    for i, args in enumerate(actionArgsList):
        args['$parallel-id'] = i

        checkTask = _CfgCheckTask(env = None)
        checkTask.stopRunnerOnError = not tryall
        checkTask.conf = cfgCtx
        checkTask.bld = runnerCtx # to use in task.log_display(task.generator.bld)

        # bind a logger that will keep the info in memory
        checkTask.logger = log.makeMemLogger(str(id(checkTask)), cfgCtx.logger)

        checkTask.call = { 'name' : args.pop('$func-name'), 'args' : args }

        tasks.append(checkTask)

    bconfpath = bconf.path

    _applyParallelActionsDeps(tasks, bconfpath)

    def getTasksGenerator():
        yield tasks
        while 1:
            yield []

    runnerCtx.producer = scheduler = Runner.Parallel(runnerCtx, Options.options.jobs)
    scheduler.biter = getTasksGenerator()

    cfgCtx.endMsg('started')
    try:
        scheduler.start()
    except waferror.WafError as ex:
        if ex.msg.startswith('Task dependency cycle'):
            msg = "Infinite recursion was detected in parallel config actions."
            msg += " Check all parameters 'before' and 'after'."
            raise error.ZenMakeConfError(msg, confpath = bconfpath)
        # it's a different error
        raise

    # flush the logs in order into the config.log
    for tsk in tasks:
        tsk.logger.memhandler.flush()

    _processParallelActionsResults(params, runnerCtx, scheduler)

def runActionsInParallel(actionArgs, params):
    """
    Run actions in parallel
    """

    cfgCtx     = params['cfgCtx']
    taskName   = params['taskName']

    subactions = actionArgs.pop('actions', [])
    if not subactions:
        msg = "Nothing to configure in parallel for task %r" % taskName
        log.warn(msg)
        return

    supportedActions = (
        'call-pyfunc', 'check-headers', 'check-libs', 'check-code',
    )

    parallelActionArgsList = []
    params['parallel-actions'] = parallelActionArgsList

    for action in subactions:
        errMsg = None
        if isinstance(action, maptype):
            actionName = action.get('do')
            if not actionName:
                errMsg = "Parameter 'do' not found in parallel action '%r'" % action
            elif actionName not in supportedActions:
                errMsg = "action %r can not be used inside the 'parallel'" % actionName
                errMsg += ", task: %r!" % taskName
        elif callable(action):
            pass
        else:
            errMsg = "Action '%r' is not supported." % action

        if errMsg:
            cfgCtx.fatal(errMsg)

    _handleActions(subactions, params)
    params.pop('parallel-actions', None)

    if not parallelActionArgsList:
        return

    for args in parallelActionArgsList:
        args['msg'] = "  %s" % args['msg']

    _runActionsInParallelImpl(params, parallelActionArgsList, **actionArgs)

_cmnActionsFuncs = {
    'call-pyfunc'    : callPyFunc,
    'find-program'   : findProgram,
    'find-file'      : findFile,
    'toolconfig'     : doToolConfig,
    'parallel'       : runActionsInParallel,
}

_actionsTable = { x:_cmnActionsFuncs.copy() for x in ToolchainVars.allLangs() }

def regActionFuncs(lang, funcs):
    """
    Register functions for configuration actions
    """

    _actionsTable[lang].update(funcs)

def _handleActions(actions, params):

    for actionArgs in actions:
        if callable(actionArgs):
            actionArgs = {
                'do' : 'call-pyfunc',
                'func' : actionArgs,
            }
        else:
            # actionArgs is changed in conf action func below
            actionArgs = actionArgs.copy()

        ctx = params['cfgCtx']
        taskName = params['taskName']

        action = actionArgs.pop('do', None)
        if action is None:
            msg = "No 'do' in the configuration action %r for task %r!" \
                    % (actionArgs, taskName)
            ctx.fatal(msg)

        targetLang = params['taskParams'].get('$tlang')
        table = _actionsTable.get(targetLang, _cmnActionsFuncs)
        func = table.get(action)
        if not func:
            msg = "Unsupported action %r in the configuration actions for task %r!" \
                    % (action, taskName)
            ctx.fatal(msg)

        func(actionArgs, params)

_exportedActionsFuncs = {
    'check'             : _applyCheckResults,
    'find-program'      : _applyFindProgramResults,
    'find-file'         : _applyFindFileResults,
    'tool-config'       : _applyToolConfigResults,
    'write-conf-header' : _applyWriteConfigHeaderResults,
}

def _exportConfigActions(cfgCtx, taskParams):

    if not taskParams.get('export-config-results', False):
        return

    exports = []
    storedActions = taskParams['$stored-actions']
    for actionData in storedActions:
        func = _exportedActionsFuncs.get(actionData['type'])
        assert func is not None
        exports.append([func, actionData['data']])

    def applyExports(rdeps, exports):

        for name in rdeps:
            depTaskParams = cfgCtx.allTasks.get(name)
            if not depTaskParams:
                continue

            cfgCtx.setenv(depTaskParams['$task.variant'])
            for func, data in exports:
                data['$task-params'] = depTaskParams
                func(cfgCtx, data)

            applyExports(depTaskParams.get('$ruse', []), exports)

    applyExports(taskParams.get('$ruse', []), exports)

    # return back the current task env
    cfgCtx.setenv(taskParams['$task.variant'])

def runActions(cfgCtx):
    """
    Run configuration actions
    """

    _handleLoadedActionsCache(cfgCtx.getConfCache())

    rootbconf = cfgCtx.bconfManager.root
    buildtype = rootbconf.selectedBuildType
    printLogo = True

    tasksList = cfgCtx.allOrderedTasks

    for taskParams in tasksList:

        cfgCtx.setenv(taskParams['$task.variant'])

        # set context path, not sure it's really necessary
        #cfgCtx.path = cfgCtx.getPathNode(bconf.confdir)

        taskParams['$stored-actions'] = deque()

        actions = taskParams.get('configure', [])
        if not actions:
            continue

        taskName = taskParams['name']

        if printLogo:
            log.printStep('Running configuration actions')
            printLogo = False
        #log.info('.. Actions for the %r:' % taskName)

        bconf = taskParams['$bconf']

        params = {
            'cfgCtx' : cfgCtx,
            'bconf' : bconf,
            'buildtype' : buildtype,
            'taskName' : taskName,
            'taskParams' : taskParams,
        }

        _handleActions(actions, params)

        _exportConfigActions(cfgCtx, taskParams)

    for taskParams in tasksList:
        taskParams.pop('$stored-actions')

    # switch to the root env
    cfgCtx.variant = ''

    # mark cache memory as ready to free
    _cache.clear()
