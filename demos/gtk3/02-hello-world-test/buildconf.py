
tasks = {
    'hello' : {
        'features' : 'cprogram',
        'source'   : 'hello.c',
        'config-actions'  : [
            { 
                'do' : 'pkgconfig', 
                'packages' : 'gtk+-3.0 > 1 pango gtk+-3.0 <= 100 ',
                'tool-atleast-version' : '0.1',
                'pkg-version' : True,  
                #'defnames' : False,
                'defnames' : { 
                    'gtk+-3.0' : { 'have' : 'WE_HAVE_GTK3', 'version': 'GTK3_VER' },
                    'pango' : { 'version': 'LIBPANGO_VER' }, 
                },
                #'mandatory' : False,
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

