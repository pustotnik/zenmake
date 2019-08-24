
import os
import getpass
import tempfile
joinpath  = os.path.join

username = getpass.getuser()     # portable way to get user name
tmpdir   = tempfile.gettempdir() # portable way to get temp directory

#realbuildroot = joinpath(tmpdir, username, 'projects', 'complex-unittest', 'build')

tasks = {
    'shlib' : {
        'features' : 'cxxshlib runcmd',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'includes' : '.',
        'run'      : {
            'cmdline' : "echo 'This is runcmd in task \"shlib\"'",
        },
    },
    'stlib' : {
        'features' : 'cxxstlib',
        'source'   :  dict( include = 'stlib/**/*.cpp' ),
        'includes' : '.',
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
        'run'      : {
            'cmdline' : "echo 'This is runcmd in task \"complex\"'",
            #'repeat'  : 2,
        },
    },
    'stlib.test' : {
        'features' : 'cxxprogram test',
        'source'   : 'tests/test_stlib.cpp',
        'use'      : 'stlib',
    },
    'test.py' : {
        #'features' : 'runcmd',
        'features' : 'test',
        'run'      : {
            'cmdline' : 'python tests/test.py',
            'cwd'     : '.',
        },
        'use'      : 'complex',
        'conftests'  : [ dict(act = 'check-programs', names = 'python'), ]
    },
    'shlib.test' : {
        'features'    : 'cxxprogram test',
        'source'      : 'tests/test_shlib.cpp',
        'use'         : 'shlib',
        'run'      : {
            'cmdline' : '${PROGRAM} a b c',
            #'cwd'     : '.', # can be path relative to current project root path
            #'cwd'     : '.1',
            'env'     : { 'AZ' : '111', },
            'repeat'  : 2,
            'timeout' : 10, # in seconds, Python 3 only
            'shell'   : False,
        },
    },
    'shlibmain.test' : {
        'features'    : 'cxxprogram test',
        'source'      : 'tests/test_shlibmain.cpp',
        'use'         : 'shlibmain',
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

