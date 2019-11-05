
options = {
    'color': 'no',
    'jobs' : { 'build' : 4 },
    'progress' : {'any': False, 'build': True },
}

tasks = {
    'shlib' : {
        'features' : 'shlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'includes' : 'include',
        'defines'  : ['ABC=1', 'DOIT'],
        'export-includes' : True,
        'export-defines' : True,
        'install-path' : None,
    },
    'stlib' : {
        'features' : 'stlib',
        'source'   :  dict( include = 'stlib/**/*.cpp' ),
    },
    'shlibmain' : {
        'features' : 'shlib',
        'source'   :  dict( include = 'shlibmain/**/*.cpp' ),
        'use'      : 'shlib stlib',
        'install-path' : '${PREFIX}/lbr',
    },
    'main' : {
        'features' : 'program',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'use'      : 'shlibmain',
    },
}

buildtypes = {
    # -fPIC is necessary to compile static lib
    'debug-gcc' : {
        'toolchain' : 'g++',
        'cxxflags' : '-fPIC -O0 -g',
        'linkflags' : '-Wl,--as-needed',
    },
    'release-gcc' : {
        'toolchain' : 'g++',
        'cxxflags' : '-fPIC -O2',
        'linkflags' : '-Wl,--as-needed',
    },
    'debug-clang' : {
        'toolchain' : 'clang++',
        'cxxflags' : '-fPIC -O0 -g',
    },
    'release-clang' : {
        'toolchain' : 'clang++',
        'cxxflags' : '-fPIC -O2',
    },
    'debug-msvc' : {
        'toolchain' : 'msvc',
        'cxxflags' : '/Od /EHsc',
    },
    'release-msvc' : {
        'toolchain' : 'msvc',
        'cxxflags' : '/O2 /EHsc',
    },
    'default' : 'debug-gcc',
}

platforms = {
    'linux' : {
        'valid'   : 'debug-gcc debug-clang release-gcc release-clang',
        'default' : 'debug-gcc',
    },
    # Mac OS
    'darwin' : {
        'valid'   : 'debug-clang release-clang',
        'default' : 'debug-clang',
    },
    'windows' : {
        'valid'   : 'debug-msvc release-msvc',
        'default' : 'debug-msvc',
    },
}

