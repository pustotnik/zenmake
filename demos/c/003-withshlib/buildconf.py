
tasks = {
    'util' : {
        'features' : 'c cshlib',
        'source'   :  dict( include = 'shlib/**/*.c' ),
        'includes' : '.',
    },
    'test' : {
        'features' : 'c cprogram',
        'source'   :  dict( include = 'prog/**/*.c' ),
        'includes' : '.',
        'use'      : 'util',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

