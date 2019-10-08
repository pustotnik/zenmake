
tasks = {
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   :  dict( include = '**/*.cpp' ),
        'includes' : '.',
    },
}

buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}

