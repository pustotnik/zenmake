
tasks = {
    'util' : {
        'features' : 'cxxshlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'includes' : '.',
        'config-actions'  : [
            { 'do' : 'check-headers', 'names' : 'cstdio iostream' },
        ],
    },
    'prog' : {
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

