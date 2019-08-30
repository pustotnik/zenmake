
tasks = {
    'simple' : {
        'features' : 'cxxprogram',
        'source'   :  {
            'include' : '**/*.cpp',
            'exclude' : '**/test*',
        },
        'rpath' : '.',
    },
    'simple.tests' : {
        'features' : 'cxxprogram test',
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
