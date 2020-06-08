
tasks = {
    'extra' : {
        'features' : 'shlib',
        'source'   : 'src/extra.cpp',
        'includes' : 'src',
        'use'      : 'corelib',
        'config-actions'  : [
            dict(do = 'check-headers', names = 'iostream'),
        ],
    },
    'engine' : {
        'features' : 'shlib',
        'source'   :  dict( include = 'src/**/*.cpp', exclude = 'src/extra*' ),
        'includes' : 'src',
        'use'      : 'extra',
        'export-includes' : True,
        'config-actions'  : [
            dict(do = 'check-headers', names = 'iostream'),
        ],
    },
}
