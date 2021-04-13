
tasks = {
    'util' : {
        'includes' : 'headers',
        'export'   : 'includes',
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   : 'prog/**/*.cpp',
        'use'      : 'util',
    },
}

