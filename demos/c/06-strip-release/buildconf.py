
# Example of using 'strip' utility on Linux

tasks = {
    'program' : {
        'features' : 'cprogram',
        'source'   : 'test.c util.c',
        'conftests' : [ dict(act = 'check-programs', names = 'strip'), ],
        'run': '${STRIP} ${TARGET}',
    },
}

buildtypes = {
    'release' : {
        'cflags' : '-O2',
    }
}

