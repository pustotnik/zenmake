
tasks = {
    'simple' : {
        'features' : 'cxxprogram',
        'source'   :  {
            'include' : '**/*.cpp',
            'exclude' : '**/test*',
        },
    },
    'simple.tests' : {
        'features' : 'cxxprogram test',
        'source'   :  {
            'include' : '**/*.cpp',
            'exclude' : 'main.cpp',
        },
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}
