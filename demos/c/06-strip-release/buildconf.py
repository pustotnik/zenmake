
# Example of using 'strip' utility on Linux

tasks = {
    'program' : {
        'features' : 'cprogram',
        'source'   : 'test.c util.c',
        'config-actions' : [ { 'do' : 'find-program', 'names' : 'strip'} ],
        'run': '${STRIP} ${TARGET}',
    },
}

buildtypes = {
    'release' : {
        'cflags' : '-O2',
    }
}

