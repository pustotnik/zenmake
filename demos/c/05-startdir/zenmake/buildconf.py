
startdir = '../project'
buildroot = '../build'

tasks = {
    'util' : {
        'features' : 'cshlib',
        'source'   :  dict( include = 'src/shlib/**/*.c' ),
        'includes' : 'includes',
        'export-includes': True,
        'config-actions'  : [
            dict(do = 'check-headers', names = 'stdio.h'),
        ],
    },
    'test' : {
        'features' : 'cprogram',
        'source'   :  dict( include = 'src/prog/**/*.c' ),
        'use'      : 'util',
        'config-actions'  : [
            dict(do = 'check-headers', names = 'stdio.h'),
        ],
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c',
    },
    'default' : 'debug',
}

