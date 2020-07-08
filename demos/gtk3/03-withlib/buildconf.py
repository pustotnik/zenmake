
tasks = {
    'builder.ui' : {
        'source' : 'gui/builder.ui',
        'run': "cp ${SRC} ${TGT}",
    },
    'gui' : {
        'features' : 'cshlib',
        'source'   : 'gui/*.c',
        'use'      : 'builder.ui',
        'config-actions'  : [
            { 'do' : 'pkgconfig', 'packages' : 'gtk+-3.0' },
        ],
        'export-config-actions' : True,
    },
    'app' : {
        'features' : 'cprogram',
        'source'   : 'app/*.c',
        'use'  : 'gui',
        #'rpath' : '.',
    },
}

buildtypes = {
    'debug'   : { 'cflags' : '-O0 -g' },
    'release' : { 'cflags' : '-O2' },
    'default' : 'debug',
}

