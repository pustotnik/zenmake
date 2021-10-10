
buildroot = '_build'

subdirs = [
    'libs/core',
    'libs/engine',
    'main',
]

buildtypes = {
    'debug' : {
        'toolchain.select' : {
            'default': 'g++',
            'darwin' : 'clang++',
            'windows': 'msvc',
        },
        'cflags.select' : {
            'gcc'     : '-fPIC -O0 -g',
            'clang'   : '-fPIC -O0 -g',
            'msvc'    : '/Od',
        },
        'cxxflags.select' : {
            'g++'     : '-fPIC -O0 -g',
            'clang++' : '-fPIC -O0 -g',
            'msvc'    : '/Od /EHsc',
        },
        'linkflags.select' : {
            'g++': '-Wl,--as-needed',
        },
    },
    'release' : {
        'toolchain.select' : {
            'default': 'g++',
            'darwin' : 'clang++',
            'windows': 'msvc',
        },
        'cflags.select' : {
            'gcc'     : '-fPIC -O2',
            'clang'   : '-fPIC -O2',
            'msvc'    : '/O2',
        },
        'cxxflags.select' : {
            'g++'     : '-fPIC -O2',
            'clang++' : '-fPIC -O2',
            'msvc'    : '/O2 /EHsc',
        },
        'linkflags.select' : {
            'g++': '-Wl,--as-needed',
        },
    },

    'default' : 'debug',
}

byfilter = [
    {
        'for' : 'all',
        'set' : {
          'rpath' : '.',
        }
    },
]
