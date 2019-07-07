
buildtypes = {
    'debug' : {
        'toolchain' : 'auto-c++',
    },
    'default' : 'debug',
}

tasks = {
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   :  dict( include = '**/*.cpp' ),
        'includes' : '.',
    },
}
