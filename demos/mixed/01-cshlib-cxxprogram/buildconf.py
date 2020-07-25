
substvars = {
    'SCRIPTS_DIR' : 'scripts',
}

tasks = {
    'util' : {
        'features'  : 'cshlib',
        'source'    :  dict( include = 'shlib/**/*.c' ),
        'includes'  : '.',
        #'toolchain' : 'auto-c',

        # 'install-files' testing
        'install-files' : [
            {
                # copy whole directory
                'src' : 'scripts',
                'dst': '${PREFIX}/share/${PROJECT_NAME}/${SCRIPTS_DIR}',
                'chmod' : 0o755,
            },
            {
                # copy all files from directory
                'src' : 'scripts/*',
                'dst': '${PREFIX}/share/${PROJECT_NAME}/${SCRIPTS_DIR}2',
                'chmod' : '755',
                # copy links as is
                'follow-symlinks' : False,
            },
            {
                # copy all files from directory recursively
                'src' : 'scripts/**/', # the same as 'scripts/**'
                'dst': '${PREFIX}/share/${PROJECT_NAME}/${SCRIPTS_DIR}3',
            },
            {
                # copy as
                'do' : 'copy-as',
                'src' : 'scripts/my-script.py',
                'dst': '${PREFIX}/share/${PROJECT_NAME}/${SCRIPTS_DIR}/mtest.py',
                'chmod' : '750',
            },
        ],
    },
    'test' : {
        'features'  : 'cxxprogram',
        'source'    :  dict( include = 'prog/**/*.cpp' ),
        'includes'  : '.',
        'use'       : 'util',
        #'toolchain' : 'auto-c++',

        # 'install-files' testing
        'install-files.select' : {
            'linux' : [
                {
                    # symlink
                    'src' : '${PREFIX}/share/${PROJECT_NAME}/${SCRIPTS_DIR}/mtest.py',
                    'symlink': '${PREFIX}/share/${PROJECT_NAME}/${SCRIPTS_DIR}/mtest-link.py',
                },
            ],
        },
    },
}

