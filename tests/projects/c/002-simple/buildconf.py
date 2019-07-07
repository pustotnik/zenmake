
#srcroot = 'src'

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

# config of tasks, this var is used by wscript
tasks = {
    'test' : {
        'features'   : 'c cprogram',
        #'source'     :  dict( include = '*.c' ),
        'source'     : 'test.c util.c',
        'includes'   : '.',
    },
}
