
tasks = {
    'extra' : {
        'features' : 'shlib',
        'source'   : 'src/extra.cpp',
        'includes' : 'src',
        'use'      : 'corelib',
        'conftests'  : [
            #dict(act = 'check-headers', names = 'iostream'),
        ],
    },
    'engine' : {
        'features' : 'shlib',
        'source'   :  dict( include = 'src/**/*.cpp', exclude = 'src/extra*' ),
        'includes' : 'src',
        'use'      : 'extra',
        'export-includes' : True,
        'conftests'  : [
            #dict(act = 'check-headers', names = 'iostream'),
        ],
    },
}
