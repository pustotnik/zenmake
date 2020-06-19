
tasks = {
    'hello' : {
        'features' : 'program',
        'source'   : 'hello.cpp',
        'config-actions'  : [
            { 'do' : 'check-headers', 'names' : 'iostream' },
            { 
                'do' : 'toolconfig', 
                'toolname' : 'sdl2-config',
                #'args' : '--cflags --libs',
                #'defname' : 'SDL2',
            },
            { 
                'do' : 'toolconfig', 
                'toolname' : 'sdl2-config',
                'msg' : 'Getting SDL2 version',
                'args' : '--version',
                'parse-as' : 'entire',
                'defname' : 'SDL2_VERSION',
            },
        ],
    },
}

buildtypes = {
    'debug' : {
        'cflags' : '-O0 -g',
    },
    'release' : {
        'cflags' : '-O2',
    },
    'default' : 'debug',
}

