
features = {
    #'provide-dep-targets' : True,
}

zmdepdir = '../zmdep'
dependencies = {
    'zmdep' : {
        'rootdir': zmdepdir,
        'export-includes' : zmdepdir,
    },
}

tasks = {
    'myutil' : {
        'features' : 'cxxshlib',
        'source'   : 'shlib/**/*.cpp',
        'use' : 'zmdep:calclib zmdep:printlib',
        'config-actions'  : [
            { 'do' : 'check-headers', 'names' : 'cstdio iostream' },
        ],
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   : 'prog/**/*.cpp',
        'use' : 'myutil',
        #'rpath' : '.', # to have ability to run from the build directory
    },
}

buildtypes = {
    'debug' : {
        'cxxflags.select' : {
            'default': '-fPIC -O0 -g', # g++/clang++
            'msvc' : '/Od /EHsc',
        },
    },
    'release' : {
        'cxxflags.select' : {
            'default': '-fPIC -O2', # g++/clang++
            'msvc' : '/O2 /EHsc',
        },
    },
    'default' : 'debug',
}

