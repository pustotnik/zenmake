
tasks = {
    'dll' : {
        #'features' : 'dshlib',
        'features' : 'shlib',
        'source'   : 'src/dll.d',
    },
    'staticlib' : {
        #'features' : 'dstlib',
        'features' : 'stlib',
        'source'   : 'src/static_lib.d',
    },
    'test' : {
        #'features' : 'dprogram',
        'features' : 'program',
        'source'   : 'src/main.d',
        'includes' : 'src',
        'use'      : 'staticlib dll',
    },
}

buildtypes = {
    'release' : {
        #'toolchain': 'auto-d',
        #'toolchain': 'ldc2',
        #'toolchain': 'dmd',
        #'toolchain': 'gdc',

        'dflags' : '-O',
    }
}

toolchains = {
    'gdc': {
        'LINKFLAGS' : '-pthread', # just as an example of linker flags
    },
}

