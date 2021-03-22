
buildroot = '_build'

subdirs = [
    'libs/core',
    'libs/engine',
    'main',
]

buildtypes = {
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
        'cflags' : '/Od',
        'cxxflags' : '/Od /EHsc',
    },
    'release-msvc' : {
        'toolchain' : 'msvc',
        'cflags' : '/O2',
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

byfilter = [
    {
        'for' : 'all',
        'set' : {
          'rpath' : '.',
        }
    },
]
