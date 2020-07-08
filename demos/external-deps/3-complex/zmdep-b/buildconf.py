
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
        'source'   : 'print/**/*.c',
        'use' : 'zmdep-a:printlib',
        'config-actions'  : [
            # ZenMake tests only: check there is no problem with this conf action
            dict(do = 'check-libs'),
        ],
    },
    'service' : {
        'features' : 'cprogram',
        'source'   : 'service/**/*.c',
        'use'      : 'calc print',
        'config-actions' : [
            dict(do = 'check-headers', names = 'stdio.h'),
            # ZenMake tests only: check there is no problem with this conf action
            dict(do = 'check-libs'),
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

