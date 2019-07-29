
tasks = {
    'util' : {
        'features'  : 'c cshlib',
        'source'    :  dict( include = 'shlib/**/*.c' ),
        'includes'  : '.',
        'toolchain' : 'auto-c',
    },
    'test' : {
        'features'  : 'cxx cxxprogram',
        'source'    :  dict( include = 'prog/**/*.cpp' ),
        'includes'  : '.',
        'use'       : 'util',
        'toolchain' : 'auto-c++',
    },
}

buildtypes = {
    'debug' : {},
    'default' : 'debug',
}

