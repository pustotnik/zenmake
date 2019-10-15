
tasks = {
    'simple' : {
        'features' : 'program',
        'source'   :  {
            'include' : '**/*.cpp',
            'exclude' : '**/test*',
        },
        'rpath' : '.',
    },
    'simple.tests' : {
        'features' : 'program test',
        'source'   :  {
            'include' : '**/*.cpp',
            'exclude' : 'main.cpp',
        },
        'rpath' : '.',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}
