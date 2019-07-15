
buildtypes = {
    'default' : 'debug',
}

tasks = {
    'util' : {
        'features' : 'c cshlib',
        'source'   :  dict( include = 'shlib/**/*.c' ),
        'includes' : '.',
        'buildtypes' : {
            'debug' : {
                'toolchain' : 'auto-c',
            },
        },
    },
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'includes' : '.',
        'use'      : 'util',
        'buildtypes' : {
            'debug' : {
                'toolchain' : 'auto-c++',
            },
        },
    },
}
