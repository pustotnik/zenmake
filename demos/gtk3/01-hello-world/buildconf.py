
tasks = {
    'hello' : {
        'features' : 'program',
        'source'   : 'hello.c',
        'config-actions'  : [
            { 'do' : 'pkgconfig', 'packages' : 'gtk+-3.0' },
        ],
    },
}

buildtypes = {
    'debug' : {
        'cflags' : '-O0 -g',
    },
    'release' : {
        'cflags' : '-O2',
    },
    'default' : 'debug',
}

