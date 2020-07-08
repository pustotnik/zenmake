
tasks = {
    'util' : {
        'features' : 'cxxshlib',
        'source'   : 'shlib/**/*.cpp',
        'includes' : '.',
        'config-actions'  : [
            { 'do' : 'check-headers', 'names' : 'cstdio iostream' },
        ],
    },
    'prog' : {
        'features' : 'cxxprogram',
        'source'   : 'prog/**/*.cpp',
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

