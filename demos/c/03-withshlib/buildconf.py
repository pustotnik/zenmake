
tasks = {
    'util' : {
        'features' : 'cshlib',
        'source'   :  dict( include = 'shlib/**/*.c' ),
        'includes' : '.',
    },
    'test' : {
        'features' : 'cprogram',
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

