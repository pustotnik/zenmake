
tasks = {
    'extra' : {
        'features' : 'cxxshlib',
        'source'   : 'src/extra.cpp',
        'includes' : 'src',
        'use'      : 'corelib',
        'configure'  : [
            dict(do = 'check-headers', names = 'iostream'),
        ],
    },
    'engine' : {
        'features' : 'cxxshlib',
        'source'   :  dict( incl = 'src/**/*.cpp', excl = 'src/extra*' ),
        'includes' : 'src',
        'use'      : 'extra',
        'export-includes' : True,
        'configure'  : [
            dict(do = 'check-headers', names = 'iostream'),
        ],
    },
}
