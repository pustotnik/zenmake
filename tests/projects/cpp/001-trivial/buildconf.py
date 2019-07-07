
buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}

tasks = {
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   : 'test.cpp',
    },
}
