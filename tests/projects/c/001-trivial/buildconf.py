
tasks = {
    'test' : {
        'features' : 'c cprogram',
        'source'   : 'test.c',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

