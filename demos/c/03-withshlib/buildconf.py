
tasks = {
    'util' : {
        'features' : 'cshlib',
        'source'   : 'shlib/**/*.c',
        'includes' : '.',
        'config-actions'  : [
            { 'do' : 'check-headers', 'names' : 'stdio.h' },
        ],
        'ver-num' : '0.1.2',
    },
    'test' : {
        'features' : 'cprogram',
        'source'   : 'prog/**/*.c',
        'includes' : '.',
        'use'      : 'util',
        'config-actions'  : [
            { 'do' : 'check-headers', 'names' : 'stdio.h' },
        ],
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

