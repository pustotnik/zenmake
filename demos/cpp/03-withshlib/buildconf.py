
tasks = {
    'util' : {
        'features' : 'cxxshlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'includes' : '.',
        'conftests'  : [
            dict(act = 'check-headers', names = 'cstdio iostream'),
        ],
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'includes' : '.',
        'use'      : 'util',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}

