
tasks = {
    'test' : {
        #'features' : 'dprogram',
        'features' : 'program',
        'source'   :  dict( include = '**/*.d' ),
    },
}

buildtypes = {
    'debug' : {
        #'toolchain': 'auto-d',
        #'toolchain': 'ldc2',
        #'toolchain': 'dmd',
    }
}

