
features = {
    'db-format' : 'py',
}

foolibdir = '../foo-lib'

def triggerConfigure(**kwargs):
    #print(kwargs)
    return False

dependencies = {
    'foo-lib-d' : {
        'rootdir': foolibdir,
        'export-includes' : foolibdir,
        'targets': {
            'shared-lib' : {
                'dir' : foolibdir + '/_build_/debug',
                'type': 'shlib',
                'name': 'fooutil',
            },
            'static-lib' : {
                'dir' : foolibdir + '/_build_/debug',
                'type': 'stlib',
                'name': 'fooutil',
            },
        },
        'rules' : {
            'configure': { # just for testing
                'cmd' : './configure',
                'shell' : True,
                'trigger' : {
                    'paths-dont-exist' : dict(
                        startdir = foolibdir,
                        include = '**/*.label',
                    ),
                    'func' : triggerConfigure,
                },
            },
            'build' : 'make debug',
            #'build' : {
            #    'cmd' : 'make debug',
            #    'shell' : False,
            #},
            #'clean' : 'make cleandebug',
            'clean' : {
                # clean 'foo-lib' with command 'clean', it's just demo
                'cmd' : 'make cleandebug',
                'shell' : False,
                'zm-commands' : 'clean',
            },
        },
    },
    'foo-lib-r' : {
        'rootdir': foolibdir,
        'export-includes' : foolibdir,
        'targets': {
            'shared-lib' : {
                'dir' : foolibdir + '/_build_/release',
                'type': 'shlib',
                'name': 'fooutil',
            },
            'static-lib' : {
                'dir' : foolibdir + '/_build_/release',
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
        'source'   :  { 'include' : 'shlib/**/*.cpp' },
        'use.select' : {
            'debug'   : 'foo-lib-d:static-lib',
            'release' : 'foo-lib-r:static-lib',
        },
        'conftests'  : [
            { 'act' : 'check-headers', 'names' : 'cstdio iostream' },
        ],
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   :  { 'include' : 'prog/**/*.cpp' },
        'includes' : foolibdir,
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

