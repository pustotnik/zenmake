
tasks = {
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   : 'test.cpp',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}

