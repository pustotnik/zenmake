
tasks = {
    'gen-code1' : {
        'configure' : [ dict(do = 'find-program', names = 'python'), ],
        'run' : '${PYTHON} ${TOP_DIR}/gencode.py ${BUILDTYPE_DIR}/generated',
        'target' : '',
        'export' : 'config-results',
    },
    'gen-code2' : {
        'run' : '${PYTHON} ${TOP_DIR}/gencode.py ${BUILDTYPE_DIR}/generated step2',
        'target' : '',
        'use'    : 'gen-code1',
        'group-dependent-tasks' : True,
    },
    'app' : {
        'features' : 'cprogram',
        'source'   : [
            '*.c',
            { 'incl': '**/*.c', 'startdir' : '${BUILDTYPE_DIR}/generated' },
            # another way for the same result:
            #{ 'incl': 'generated/**/*.c', 'startdir' : '${BUILDTYPE_DIR}' },
        ],
        'use' : 'gen-code2',
    },
}

buildtypes = {
    'debug' : {}
}

