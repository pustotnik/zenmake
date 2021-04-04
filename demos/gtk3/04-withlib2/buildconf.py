
project = {
    'name' : 'mygtk3app2',
}

tasks = {
    'gui-resources' : {
        'config-actions'  : [
            # find 'glib-compile-resources' by pkg-config
            {
                'msg' : 'Looking for glib-compile-resources',
                'do' : 'toolconfig', 'toolname' : 'pkg-config',
                'args' : '--variable=glib_compile_resources gio-2.0',
                'parse-as' : 'entire',
                'var' : 'COMPILE_RES',
            },
            # it's different and more simple way to find tool 'glib-compile-resources':
            #{ 'do' : 'find-program', 'names' : 'glib-compile-resources', 'var' : 'COMPILE_RES' },
        ],
        'source' : 'gui/gui.gresource.xml',
        'target' : 'generated/resources.c',
        'run': "${COMPILE_RES} ${SRC} --target=${TGT} --sourcedir=${TOP_DIR}/gui --generate-source",
    },
    'gui' : {
        'features' : 'cshlib',
        'source'   : 'gui/*.c generated/resources.c',
        'use'      : 'gui-resources',
        'ver-num'  : '0.1.2',
        'config-actions'  : [
            { 'do' : 'pkgconfig', 'packages' : 'gtk+-3.0' },
        ],
        'export-config-results' : True,
    },
    'gtk3demo2' : {
        'features' : 'cprogram',
        'source'   : 'app/*.c',
        'use'  : 'gui',
        #'rpath' : '.',
    },
}

buildtypes = {
    'debug'   : { 'cflags' : '-O0 -g' },
    'release' : { 'cflags' : '-O2' },
    'default' : 'debug',
}

