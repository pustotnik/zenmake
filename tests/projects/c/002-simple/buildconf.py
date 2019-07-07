
buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

tasks = {
    'test' : {
        'features' : 'c cprogram',
        'source'   : 'test.c util.c',
        'includes' : '.',
    },
}
