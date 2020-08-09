
tasks = {
    'gen-code1' : {
        'config-actions' : [ dict(do = 'find-program', names = 'python'), ],
        'run' : '${PYTHON} ${TOP_DIR}/gencode.py ${BUILDTYPE_DIR}/generated',
        'target' : '',
        'export-config-actions' : True,
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
            { 'include': '**/*.c', 'startdir' : '${BUILDTYPE_DIR}/generated' },
            # another way for the same result:
            #{ 'include': 'generated/**/*.c', 'startdir' : '${BUILDTYPE_DIR}' },
        ],
        'use' : 'gen-code2',
    },
}

buildtypes = {
    'debug' : {}
}

