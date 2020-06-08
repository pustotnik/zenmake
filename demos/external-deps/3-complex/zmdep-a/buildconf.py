
tasks = {
    'calclib' : {
        'features' : 'cshlib',
        'source'   :  dict( include = 'calclib/**/*.c' ),
        'ver-num'  : '1.2.4',
    },
    'printlib' : {
        'features' : 'cstlib',
        'source'   :  dict( include = 'printlib/**/*.c' ),
        'config-actions' : [
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

