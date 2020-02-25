
import os
import sys
import getpass
import tempfile
joinpath  = os.path.join

username = getpass.getuser()     # portable way to get user name
tmpdir   = tempfile.gettempdir() # portable way to get temp directory
iswin32  = os.sep == '\\' or sys.platform == 'win32' or os.name == 'nt'

#realbuildroot = joinpath(tmpdir, username, 'projects', 'complex-unittest', 'build')

def somefunc(args):
    print("somefunc: buildtype = %r" % args['buildtype'])

tasks = {
    'shlib' : {
        'features' : 'cxxshlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'includes' : '.',
        'run'      : "echo 'This is runcmd in task \"shlib\"'",
        'conftests'  : [
            dict(act = 'check-headers', names = 'iostream'),
        ],
    },
    'stlib' : {
        'features' : 'cxxstlib',
        'source'   :  dict( include = 'stlib/**/*.cpp' ),
        'includes' : '.',
        'conftests'  : [
            dict(act = 'check-headers', names = 'cstdio'),
        ],
    },
    'shlibmain' : {
        'features' : 'cxxshlib',
        'source'   :  dict( include = 'shlibmain/**/*.cpp' ),
        'includes' : '.',
        'use'      : 'shlib stlib',
    },
    'complex' : {
        'features' : 'cxxprogram runcmd',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'includes' : '.',
        'use'      : 'shlibmain',
        'run'      : "echo 'This is runcmd in task \"complex\"'",
    },
    'echo' : {
        'run'      : {
            'cmd'    : "echo 'say hello'",
            'repeat' : 2,
        },
        'use'      : 'shlibmain',
    },
    'ls' : {
        'run'      : {
            'cmd' : iswin32 and "dir /B" or "ls",
            'cwd' : '.',
        },
    },
    'test.py' : {
        'run'      : {
            'cmd'   : 'python tests/test.py',
            'cwd'   : '.',
            'env'   : { 'JUST_ENV_VAR' : 'qwerty', },
            'shell' : False,
        },
        'use'       : 'shlibmain',
        'conftests' : [ dict(act = 'check-programs', names = 'python'), ]
    },
    'altscript' : {
        'run' : { 'cmd' : '"alt script.py"', 'cwd' : '.' },
    },
    'pyfunc' : {
        'run': somefunc
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
            'cwd'   : '.',
            'shell' : False,
        },
        'use' : 'complex',
        'conftests' : [ dict(act = 'check-programs', names = 'python'), ]
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
        'conftests' : [ dict(act = 'check-headers', names = 'vector'), ]
    },
    'shlibmain-test' : {
        'features' : 'cxxprogram test',
        'source'   : 'tests/test_shlibmain.cpp',
        'use'      : 'shlibmain testcmn',
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

matrix = [
    { 'for' : {}, 'set' : { 'rpath' : '.', } },
]
