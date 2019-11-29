
startdir = '../project'
buildroot = '../build'

tasks = {
    'util' : {
        'features' : 'cshlib',
        'source'   :  dict( include = 'src/shlib/**/*.c' ),
        'includes' : 'includes',
        'export-includes': True,
    },
    'test' : {
        'features' : 'cprogram',
        'source'   :  dict( include = 'src/prog/**/*.c' ),
        'use'      : 'util',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

