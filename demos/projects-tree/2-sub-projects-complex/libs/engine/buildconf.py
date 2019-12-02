
def check():
    # some checking
    return True

tasks = {
    'extra' : {
        'features' : 'shlib',
        'source'   : 'src/extra.cpp',
        'includes' : 'src',
        'use'      : 'corelib',
        'conftests'  : [
            dict(act = 'check-headers', names = 'iostream'),
            check,
        ],
    },
    'engine' : {
        'features' : 'shlib',
        'source'   :  dict( include = 'src/**/*.cpp', exclude = 'src/extra*' ),
        'includes' : 'src',
        'use'      : 'extra',
        'export-includes' : True,
        'conftests'  : [
            dict(act = 'check-headers', names = 'iostream'),
        ],
    },
    'extra-test' : {
        'features' : 'cxxprogram test',
        'source'   : 'tests/test_extra.cpp',
        'includes' : 'src ../../tests/src',
        'use'      : 'extra testcmn',
    },
}

buildtypes = {
    'debug-gcc' : {
        'cxxflags' : '-O1 -g',
    },
}
