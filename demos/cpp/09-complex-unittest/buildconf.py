
import os
import sys
import getpass
import tempfile
joinpath  = os.path.join

username = getpass.getuser()     # portable way to get user name
tmpdir   = tempfile.gettempdir() # portable way to get temp directory
iswin32  = os.sep == '\\' or sys.platform == 'win32' or os.name == 'nt'

#realbuildroot = joinpath(tmpdir, username, 'projects', 'complex-unittest', 'build')

project = {
    'name' : 'zm-complex-unittest',
}

substvars = {
    'LS_CMD' : 'ls',
    'EXE' : 'exe',
}

def somefunc(args):
    print("somefunc: buildtype = %r" % args['buildtype'])

tasks = {
    'shlib' : {
        'features' : 'cxxshlib',
        'source'   : 'shlib/**/*.cpp',
        'includes' : '.',
        'run'      : "echo 'This is runcmd in task \"shlib\"'",
        #'configure'  : [
        #    dict(do = 'check-headers', names = 'iostream'),
        #],
        # testing of 'configure.select' feature
        'configure.select'  : {
            'default' : [
                dict(do = 'check-headers', names = 'iostream'),
            ],
            'linux' : [
                dict(do = 'check-headers', names = 'iostream cstdio'),
            ]
        }
    },
    'stlib' : {
        'features' : 'cxxstlib',
        'source'   : 'stlib/**/*.cpp',
        'includes' : '.',
        'configure'  : [
            dict(do = 'check-headers', names = 'cstdio'),
        ],
    },
    'shlibmain' : {
        'features' : 'cxxshlib',
        'source'   : 'shlibmain/**/*.cpp',
        'includes' : '.',
        'use'      : 'shlib stlib ls',
    },
    'complex' : {
        'features' : 'cxxprogram runcmd',
        'source'   : 'prog/**/*.cpp',
        'includes' : '.',
        'use'      : 'shlibmain',
        'run'      : "echo 'This is runcmd in task \"complex\"'",
        'install-path' : '${PREFIX}/${EXE}',
    },
    'echo' : {
        'run'      : {
            'cmd'    : "echo say hello",
            'repeat' : 2,
        },
        'use'      : 'shlibmain',
        'target' : '',
    },
    'ls' : {
        'substvars.select' : {
            'windows' : { 'LS_CMD' : 'dir /B' },
            'darwin' : { 'LS_CMD' : 'ls' }, # it's not needed here because root 'substvars' sets the same value
        },
        'run'      : {
            'cmd' : '${LS_CMD}',
            # a different way for the same result
            #'cmd' : iswin32 and "dir /B" or "ls",
            'cwd' : '.',
        },
        'target' : '',
    },
    'test.py' : {
        'run'      : {
            'cmd'   : '${PYTHON} tests/test.py',
            'cwd'   : '.',
            'env'   : { 'JUST_ENV_VAR' : 'qwerty', },
            'shell' : False,
        },
        'use'       : 'shlibmain',
        'configure' : [ dict(do = 'find-program', names = 'python'), ],
        'target' : '',
    },
    'altscript' : {
        'run' : { 'cmd' : '"alt script.py"', 'cwd' : '.' },
        'target' : '',
    },
    'pyfunc' : {
        'run': somefunc,
        'target' : '',
    },
    #### tasks for build/run tests
    'stlib-test' : {
        'features' : 'cxxprogram test',
        'source'   : 'tests/test_stlib.cpp',
        'use'      : 'stlib testcmn',
    },
    'test from script' : {
        'features' : 'test',
        'run'      : {
            'cmd'   : 'python tests/test.py',
            #'cmd'   : '${PYTHON} tests/test.py',
            'cwd'   : '.',
            'shell' : False,
        },
        'use' : 'complex',
        'configure' : [ dict(do = 'find-program', names = 'python'), ]
    },
    'testcmn' : {
        'features' : 'cxxshlib test',
        'source'   :  'tests/common.cpp',
        'includes' : '.',
    },
    'shlib-test' : {
        'features'    : 'cxxprogram test',
        'source'      : 'tests/test_shlib.cpp',
        'use'         : 'shlib testcmn',
        'run' : {
            'cmd' : '${TARGET} a b c',
            #'cwd'     : '.', # can be path relative to current project root path
            #'cwd'     : '.1',
            'env'     : { 'AZ' : '111', 'BROKEN_TEST' : 'false'},
            'repeat'  : 2,
            'timeout' : 10, # in seconds, Python 3 only
            'shell'   : False,
        },
        'configure' : [ dict(do = 'check-headers', names = 'vector'), ]
    },
    'shlibmain-test' : {
        'features' : 'cxxprogram test',
        'source'   : 'tests/test_shlibmain.cpp',
        'use'      : 'shlibmain testcmn',
    },
    #### this tasks is always failed but it's disabled: check param 'enabled'
    'always-failed' : {
        'run': "asdfghjklzxcvb",
        'enabled' : False,
    },
}

buildtypes = {
    # -fPIC is necessary to compile static lib
    'debug-gcc' : {
        'toolchain' : 'g++',
        'cxxflags' : '-fPIC -O0 -g',
        'linkflags' : '-Wl,--as-needed',
    },
    'release-gcc' : {
        'toolchain' : 'g++',
        'cxxflags' : '-fPIC -O2',
        'linkflags' : '-Wl,--as-needed',
    },
    'debug-clang' : {
        'toolchain' : 'clang++',
        'cxxflags' : '-fPIC -O0 -g',
    },
    'release-clang' : {
        'toolchain' : 'clang++',
        'cxxflags' : '-fPIC -O2',
    },
    'debug-msvc' : {
        'toolchain' : 'msvc',
        'cxxflags' : '/Od /EHsc',
    },
    'release-msvc' : {
        'toolchain' : 'msvc',
        'cxxflags' : '/O2 /EHsc',
    },
    'default' : 'debug-gcc',
}

platforms = {
    'linux' : {
        'valid'   : ['debug-gcc', 'debug-clang', 'release-gcc', 'release-clang' ],
        'default' : 'debug-gcc',
    },
    # Mac OS
    'darwin' : {
        'valid'   : ['debug-clang', 'release-clang' ],
        'default' : 'debug-clang',
    },
    'windows' : {
        'valid'   : ['debug-msvc', 'release-msvc' ],
        'default' : 'debug-msvc',
    },
}

byfilter = [
    { 'for' : 'all', 'set' : { 'rpath' : '.', } },
]
