
tasks = {
    'test' : {
        'features' : 'cxxprogram',
        'source'   :  dict( include = '**/*.cpp' ),
        'includes' : '.',
    },
}

buildtypes = {
    'debug' : {}
}

