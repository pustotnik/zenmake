
buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}

# config of tasks, this var is used by wscript
tasks = {
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   : 'test.cpp',
    },
}
