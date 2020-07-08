
# This is an example of a project which uses boost libraries with g++/clang++ on
# POSIX platform(Linux/MacOS) and msvc on MS Windows.

# There is special case for boost libraries on Windows.
# This setup for boost libraries installed on Windows as C:\local\boost_1_67_0
# For example, command 'choco install boost-msvc-14.1' produces such an installation.
# OS Windows needs to know path to dir with boost dlls to run program linked
# with boost dlls. In console it can be made like this:
# set PATH=C:\local\boost_1_67_0\lib64-msvc-14.1;%PATH%

tasks = {
    'util' : {
        'features' : 'cxxshlib',
        'source'   : 'shlib/**/*.cpp',
        'includes.select' : {
            'windows' : 'C:\\local\\boost_1_67_0',
        },
        'libpath.select' : {
            'windows' : r'C:\local\boost_1_67_0\lib64-msvc-14.1',
        },
        'libs' : 'boost_timer',
        'config-actions'  : [
            dict(do = 'check-headers', names = 'cmath iostream'),
            dict(do = 'check-libs'),
        ],
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   : 'prog/**/*.cpp',
        'use'      : 'util',
    },
}

conditions = {
    'util-on-windows' : {
        'task' : 'util',
        'platform' : 'windows',
    }
}

buildtypes = {
    'debug' : {
        'cxxflags.select' : {
            'default': '-fPIC -O0 -g', # g++/clang++
            'msvc' : '/Od /EHsc',
        },
        'libs.select' : {
            'util-on-windows' : 'boost_timer-vc141-mt-gd-x64-1_67',
        },
    },
    'release' : {
        'cxxflags.select' : {
            'default': '-fPIC -O2', # g++/clang++
            'msvc' : '/O2 /EHsc',
        },
        'libs.select' : {
            'util-on-windows' : 'boost_timer-vc141-mt-x64-1_67',
        },
    },
    'default' : 'debug',
}

matrix = [
    {
        'for' : { 'buildtype' : ['debug', 'release'] },
        'set' : {
            'toolchain.select' : {
                'default' : 'auto-c++',
                'windows' : 'msvc', # it's not necessary usually
            },
            'rpath' : '.', # to have ability to run from the build directory
        }
    },
]
