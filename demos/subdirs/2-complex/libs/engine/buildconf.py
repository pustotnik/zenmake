
def check():
    # some checking
    return True

def check2(**kwargs):
    task = kwargs['taskname']
    buildtype = kwargs['buildtype']
    # some checking
    #return True
    return False

tasks = {
    'extra' : {
        'features' : 'cxxshlib',
        'source'   : 'src/extra.cpp',
        'includes' : 'src',
        'use'      : 'corelib',
        'ver-num'  : '0.3.0',
        'config-actions'  : [
            dict(do = 'check-headers', names = 'cstdio iostream'),
            check,
            dict(do = 'check-headers', names = 'iostream'), # for test only
            dict(do = 'write-config-header'),
        ],
    },
    'engine' : {
        'features' : 'cxxshlib',
        'source'   :  dict( incl = 'src/**/*.cpp', excl = 'src/extra*' ),
        'includes' : 'src',
        'use'      : 'extra',
        'ver-num'  : '0.3.1',
        'export-includes' : True,
        'config-actions'  : [
            dict( do = 'check-headers', names = 'stdio.h iostream' ),
            dict( do = 'parallel', actions = [
                    dict(do = 'check-headers', names = 'cstdio iostream', id = 'first'),
                    dict(do = 'check-headers', names = 'stdlib.h', after = 'first'),
                    dict(do = 'check-headers', names = 'stdlibasd.h', mandatory = False),
                    # for test only
                    dict(do = 'check-headers', names = 'iostream'),
                    dict(do = 'check-headers', names = 'iostream'),
                    dict(do = 'check-headers', names = 'iostream'),
                    check,
                    dict(do = 'call-pyfunc', func = check2, mandatory = False),
              ],
              #tryall = True,
              tryall = False,
              #mandatory = False,
            ),
            dict( do = 'write-config-header'),
            dict( do = 'check-headers', names = 'string vector' ),
        ],
        'export-config-actions' : True,
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
