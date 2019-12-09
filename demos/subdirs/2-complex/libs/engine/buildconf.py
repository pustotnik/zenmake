
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
            dict(act = 'check-headers', names = 'cstdio iostream'),
            check,
            dict(act = 'check-headers', names = 'iostream'), # for test only
            dict(act = 'write-config-header'),
        ],
    },
    'engine' : {
        'features' : 'shlib',
        'source'   :  dict( include = 'src/**/*.cpp', exclude = 'src/extra*' ),
        'includes' : 'src',
        'use'      : 'extra',
        'export-includes' : True,
        'conftests'  : [
            dict( act = 'check-headers', names = 'stdio.h iostream' ),
            dict( act = 'parallel',
              checks = [
                    dict(act = 'check-headers', names = 'cstdio iostream'),
                    dict(act = 'check-headers', names = 'stdlib.h'),
                    dict(act = 'check-headers', names = 'stdlibasd.h', mandatory = False),
                    # for test only
                    dict(act = 'check-headers', names = 'iostream'),
                    dict(act = 'check-headers', names = 'iostream'),
                    dict(act = 'check-headers', names = 'iostream'),
              ],
            ),
            dict(act = 'write-config-header'),
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
