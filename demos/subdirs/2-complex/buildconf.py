
buildroot = '_build'

project = { 'version' : '0.3.1-dev' }

features = {
    'db-format' : 'msgpack',
}

subdirs = [
    'libs',
    'main',
    'tests',
]

buildtypes = {
    'debug-gcc' : {
        'toolchain' : 'g++',
        'cxxflags' : '-O0 -g',
        'linkflags' : '-Wl,--as-needed',
    },
    'release-gcc' : {
        'toolchain' : 'g++',
        'cxxflags' : '-O2',
        'linkflags' : '-Wl,--as-needed',
    },
    'debug-clang' : {
        'toolchain' : 'clang++',
        'cxxflags' : '-O0 -g',
    },
    'release-clang' : {
        'toolchain' : 'clang++',
        'cxxflags' : '-O2',
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

matrix = [
    {
        'for' : {}, # for all
        'set' : {
          'rpath' : '.',
        }
    },
]
