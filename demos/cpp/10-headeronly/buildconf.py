
tasks = {
    'util' : {
        'includes' : 'headers',
        'export-includes' : True,
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'use'      : 'util',
    },
}

