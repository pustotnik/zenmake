
features = {
    'db-format' : 'py',
}

dependencies = {
    'foo-lib-d' : {
        'export-includes' : '../foo-lib', # in targets?
        'targets': {
            'shared-lib' : {
                'dir' : '../foo-lib/_build_/debug',
                'type': 'shlib',
                'name': 'fooutil', # autodetect if no .so/.dll ? try to find all variants? what about vnum?
            },
            'static-lib' : {
                'dir' : '../foo-lib/_build_/debug',
                'type': 'stlib',
                'name': 'fooutil',
                #'fallback' : ???
            },
        },
        'workdir': '../foo-lib',
        'rules' : {
            #'workdir': '../foo-lib', ?
            'configure': '',
            'build' : 'make debug',
            'clean' : 'make cleandebug',
        },
    },
    'foo-lib-r' : {
        'workdir': '../foo-lib',
        'export-includes' : '../foo-lib',
        'targets': {
            'shared-lib' : {
                'dir' : '../foo-lib/_build_/release',
                'type': 'shlib',
                'name': 'fooutil',
            },
            'static-lib' : {
                'dir' : '../foo-lib/_build_/release',
                'type': 'stlib',
                'name': 'fooutil',
            },
        },
        'rules' : {
            'configure': '',
            'build' : 'make release',
            'clean' : 'make cleanrelease',
        },
    },
}

tasks = {
    'util' : {
        'features' : 'cxxshlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'use.select' : {
            'debug'   : 'foo-lib-d:static-lib',
            'release' : 'foo-lib-r:static-lib',
        },
        'conftests'  : [
            dict(act = 'check-headers', names = 'cstdio iostream'),
        ],
    },
    #'program' : {
    'прога' : {
        'features' : 'cxxprogram',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'includes' : '../foo-lib',
        # for tests
        #'libs'     : 'boost_timer',
        #'libpath'  : '/tmp',
        #######
        'use.select' : {
            'debug'   : 'util foo-lib-d:shared-lib',
            'release' : 'util foo-lib-r:shared-lib',
        },
    },
}

buildtypes = {
    'debug' : {
        'cxxflags' : '-O0 -g',
    },
    'release' : {
        'cxxflags' : '-O2',
    },
    'default' : 'debug',
}

