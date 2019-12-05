
tasks = {
    'util' : {
        'features' : 'cshlib',
        'source'   :  dict( include = 'shlib/**/*.c' ),
        'includes' : '.',
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
    },
    'test' : {
        'features' : 'cprogram',
        'source'   :  dict( include = 'prog/**/*.c' ),
        'includes' : '.',
        'use'      : 'util',
        'conftests'  : [
            dict(act = 'check-headers', names = 'stdio.h'),
        ],
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

