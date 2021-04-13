
project = {
    'name' : 'mygtk3app',
}

tasks = {
    'builder.ui' : {
        'source' : 'gui/builder.ui',
        'run': "cp ${SRC} ${TGT}",
    },
    'gui' : {
        'features' : 'cshlib',
        'source'   : 'gui/*.c',
        'use'      : 'builder.ui',
        'ver-num'  : '0.1.2',
        'configure'  : [
            { 'do' : 'pkgconfig', 'packages' : 'gtk+-3.0' },
        ],
        'export' : 'config-results',
        'install-files' : [
            {
                'src' : '${BUILDTYPE_DIR}/builder.ui',
                'dst': '${PREFIX}/share/${PROJECT_NAME}',
            },
        ],
        'defines' : 'PACKAGE_DATA_DIR=\"${PREFIX}/share/${PROJECT_NAME}\"',
    },
    'gtk3demo' : {
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

