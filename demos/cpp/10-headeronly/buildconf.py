
tasks = {
    'util' : {
        'includes' : 'headers',
        'export-includes' : True,
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   : 'prog/**/*.cpp',
        'use'      : 'util',
    },
}

