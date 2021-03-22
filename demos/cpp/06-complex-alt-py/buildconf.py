
buildtypes = {
    # -fPIC is necessary to compile static lib
    'debug-gcc' : { 'cxxflags' : '-fPIC -O0 -g' },
    'release-gcc' : { 'cxxflags' : '-fPIC -O2' },
    'debug-clang' : { 'cxxflags' : '-fPIC -O0 -g' },
    'release-clang' : { 'cxxflags' : '-fPIC -O2' },
    'debug-msvc' : { 'cxxflags' : '/Od /EHsc' },
    'release-msvc' : { 'cxxflags' : '/O2 /EHsc' },
    'default' : 'debug-gcc',
}

platforms = {
    #'linux' : { 'default' : 'release-gcc' },
    # Mac OS
    'darwin' : { 'default' : 'debug-clang' },
    #'windows' : { 'default' : 'debug-msvc' },
}

byfilter = [
    {
        'for' : 'all',
        'set' : {
          'includes' : '.',
          'rpath' : '.',
        }
    },
    {
        'for' : { 'task' : 'shlib shlibmain', },
        'set' : { 'features' : 'cxxshlib', }
    },
    {
        'for' : { 'task' : 'shlib', },
        'set' : { 'source' : 'shlib/**/*.cpp', }
    },
    {
        'for' : { 'task' : 'stlib', },
        'set' : {
            'features' : 'cxxstlib',
            'source'   : 'stlib/**/*.cpp',
        }
    },
    {
        'for' : { 'task' : 'shlibmain', },
        'set' : {
            'source'   : 'shlibmain/**/*.cpp',
            'use'      : 'shlib stlib',
        }
    },
    {
        'for' : { 'task' : 'test', },
        'set' : {
            'features' : 'cxxprogram',
            'source'   : 'prog/**/*.cpp',
            'use'      : 'shlibmain',
        }
    },
    {
        'for' : { 'buildtype' : ['debug-gcc', 'release-gcc'], 'platform' : 'linux', },
        'set' : {
            'toolchain' : 'g++',
            'linkflags' : '-Wl,--as-needed',
            #'default-buildtype' : 'debug-gcc',
            'default-buildtype' : 'release-gcc',
        }
    },
    {
        'for' : { 'buildtype' : 'release-gcc', 'platform' : 'linux', },
        'set' : { 'cxxflags' : '-fPIC -O3', }
    },
    {
        'for' : { 'buildtype' : ['debug-clang', 'release-clang'], 'platform' : 'linux darwin', },
        'set' : {
            'toolchain' : 'clang++',
        }
    },
    {
        'for' : { 'buildtype' : ['debug-msvc', 'release-msvc'], 'platform' : 'windows', },
        'set' : {
            'toolchain' : 'msvc',
            'default-buildtype' : 'debug-msvc',
        },
    },
]
