
tasks = {
    'shlib' : {
        'features' : 'cxx cxxshlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
        'includes' : '.',
    },
    'stlib' : {
        'features' : 'cxx cxxstlib',
        'source'   :  dict( include = 'stlib/**/*.cpp' ),
        'includes' : '.',
    },
    'shlibmain' : {
        'features' : 'cxx cxxshlib',
        'source'   :  dict( include = 'shlibmain/**/*.cpp' ),
        'includes' : '.',
        'use'      : 'shlib stlib',
    },
    'test' : {
        'features' : 'cxx cxxprogram',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'includes' : '.',
        'use'      : 'shlibmain',
    },
}

toolchains = {
    'custom-g++': {
        'kind'    : 'auto-c++',
        'CXX'     : 'custom-toolchain/gccemu/g++',
        'AR'      : 'custom-toolchain/gccemu/ar',
    },
    'custom-clang++': {
        'kind'    : 'auto-c++',
        'CXX'     : 'custom-toolchain/clangemu/clang++',
        'AR'      : 'custom-toolchain/clangemu/llvm-ar',
    },
}

buildtypes = {
    # -fPIC is necessary to compile static lib
    'debug-gcc' : {
        'toolchain' : 'custom-g++',
        'cxxflags' : '-fPIC -O0 -g',
        'linkflags' : '-Wl,--as-needed',
    },
    'release-gcc' : {
        'toolchain' : 'custom-g++',
        'cxxflags' : '-fPIC -O2',
        'linkflags' : '-Wl,--as-needed',
    },
    'debug-clang' : {
        'toolchain' : 'custom-clang++',
        'cxxflags' : '-fPIC -O0 -g',
    },
    'release-clang' : {
        'toolchain' : 'custom-clang++',
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
        'valid'   : ['debug-gcc', 'debug-clang', 'release-gcc', 'release-clang' ],
        'default' : 'debug-gcc',
    },
    # Mac OS
    'darwin' : {
        'valid'   : ['debug-clang', 'release-clang' ],
        'default' : 'debug-clang',
    },
    'windows' : {
        'valid'   : ['debug-msvc', 'release-msvc' ],
        'default' : 'debug-msvc',
    },
}

