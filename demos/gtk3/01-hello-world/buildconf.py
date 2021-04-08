
tasks = {
    'hello' : {
        'features' : 'cprogram',
        'source'   : 'hello.c',
        'configure'  : [
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

