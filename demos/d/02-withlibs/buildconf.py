
tasks = {
    'dll' : {
        #'features' : 'dshlib',
        'features' : 'shlib',
        'source'   : 'src/dll.d',
    },
    'static' : {
        #'features' : 'dstlib',
        'features' : 'stlib',
        'source'   : 'src/static_lib.d',
    },
    'test' : {
        #'features' : 'dprogram',
        'features' : 'program',
        'source'   : 'src/main.d',
        'includes' : 'src',
        'use'      : 'static dll',
    },
}

buildtypes = {
    'debug' : {
        #'toolchain': 'auto-d',
        #'toolchain': 'ldc2',
        #'toolchain': 'dmd',
        #'toolchain': 'gdc',
    }
}

