
features = {
    'provide-edep-targets' : True,
}

edeps = {
    'zmdep-b' : {
        'rootdir': '../zmdep-b',
        'export-includes' : '../zmdep-b',
        'buildtypes-map' : {
            'debug'   : 'mydebug',
            'release' : 'myrelease',
        },
    },
}

subdirs = [ 'libs/core', 'libs/engine' ]

tasks = {
    'main' : {
        'features' : 'cxxprogram',
        'source'   : 'main/main.cpp',
        'includes' : 'libs',
        'use'      : 'engine zmdep-b:service',
        'rpath'    : '.',
        'configure' : [
            dict(do = 'check-headers', names = 'iostream'),
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

