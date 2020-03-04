
# For testing of values with spaces

tasks = {
    'my util' : {
        'features' : 'cshlib',
        'source'   :  dict( include = '"my shlib/**/*.c"' ),
        'includes' : '"my includes"',
        'export-includes' : True,
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
    },
    'my test' : {
        'features' : 'cprogram',
        'source'   :  dict( include = '"my prog/**/*.c"' ),
        'use'      : "'my util'",
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
    },
    #######
    'my util alt' : {
        'features' : 'cshlib',
        'source'   :  '"my shlib/my util.c" "my shlib/my util2.c"',
        'includes' : '"my includes"',
        'export-includes' : True,
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
        'object-file-counter' : 2,
    },
    'my test alt' : {
        'features' : 'cprogram',
        'source'   :  '"my prog/my test.c"',
        'use'      : "'my util alt'",
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
        'object-file-counter' : 2,
    },
    ########
    'alt script' : {
        'run' : { 'cmd' : '"alt script.py"', 'cwd' : 'some scripts' },
    },
}

toolchains = {
    'my toolchain': {
        'kind' : 'auto-c',
    }
}

buildtypes = {
    'my debug' : {
        'cxxflags.select' : {
            'default': '-fPIC -O0 -g', # g++/clang++
            'msvc' : '/Od /EHsc',
        },
    },
    'my release' : {
        'cxxflags.select' : {
            'default': '-fPIC -O2', # g++/clang++
            'msvc' : '/O2 /EHsc',
        },
    },
    'default' : 'my debug',
}

matrix = [
    {
        'for' : {},
        'set' : {
            'toolchain' : '"my toolchain"',
            'rpath' : '.', # to have ability to run from the build directory
        }
    },
]

