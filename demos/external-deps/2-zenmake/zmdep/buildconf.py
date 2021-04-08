
tasks = {
    'calclib' : {
        'features' : 'cshlib',
        'source'   : 'calclib/**/*.c',
        'ver-num'  : '1.2.4',
    },
    'printlib' : {
        'features' : 'cstlib',
        'source'   : 'printlib/**/*.c',
        'configure' : [
            dict(do = 'check-headers', names = 'stdio.h'),
        ],
    },
    'service' : {
        'features' : 'cprogram',
        'source'   : 'service/**/*.c',
        'use'      : 'calclib printlib',
        'configure' : [
            dict(do = 'check-headers', names = 'stdio.h'),
        ],
    },
}

buildtypes = {
    'debug' : {
        'cflags.select' : {
            'default': '-fPIC -O0 -g', # gcc/clang
            'msvc' : '/Od',
        },
    },
    'release' : {
        'cflags.select' : {
            'default': '-fPIC -O2', # gcc/clang
            'msvc' : '/O2',
        },
    },
    'default' : 'debug',
}

