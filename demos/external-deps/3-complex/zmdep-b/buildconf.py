
dependencies = {
    'zmdep-a' : {
        'rootdir': '../zmdep-a',
        'export-includes' : '../zmdep-a',
        'buildtypes-map' : {
            'mydebug' : 'debug',
            'myrelease' : 'release',
        },
    },
}

subdirs = [ 'calc' ]

tasks = {
    'print' : {
        'features' : 'cstlib',
        'source'   :  dict( include = 'print/**/*.c' ),
        'use' : 'zmdep-a:printlib',
    },
    'service' : {
        'features' : 'cprogram',
        'source'   :  dict( include = 'service/**/*.c' ),
        'use'      : 'calc print',
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
    },
}

buildtypes = {
    'mydebug' : {
        'cflags.select' : {
            'default': '-fPIC -O0 -g', # gcc/clang
            'msvc' : '/Od',
        },
    },
    'myrelease' : {
        'cflags.select' : {
            'default': '-fPIC -O2', # gcc/clang
            'msvc' : '/O2',
        },
    },
    'default' : 'mydebug',
}

