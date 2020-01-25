
tasks = {
    'util' : {
        'features' : 'cxxshlib',
        'source'   :  dict( include = 'shlib/**/*.cpp' ),
    },
    'program' : {
        'features' : 'cxxprogram',
        'source'   :  dict( include = 'prog/**/*.cpp' ),
        'use'      : 'util',
    },
}

matrix = [
    # ==========================================================
    # === BUILDTYPES
    {
        'for' : { 'buildtype' : ['debug', 'release'] },
        'set' : {
            'toolchain' : 'auto-c++',
            'rpath' : '.', # to have ability to run from buld directory
            'default-buildtype' : 'debug',
        }
    },
    # setup for g++/clang++
    {
        'for' : { 'buildtype' : 'debug' },
        'set' : { 'cxxflags' : '-fPIC -O0 -g' }
    },
    {
        'for' : { 'buildtype' : 'release' },
        'set' : { 'cxxflags' : '-fPIC -O2' }
    },
    # setup for msvc on windows
    {
        'for' : { 'platform' : 'windows' },
        'set' : { 'toolchain' : 'msvc' } # it's not necessary usually
    },
    {
        'for' : { 'buildtype' : 'debug', 'platform' : 'windows' },
        'set' : { 'cxxflags' : '/Od /EHsc' }
    },
    {
        'for' : { 'buildtype' : 'release', 'platform' : 'windows' },
        'set' : { 'cxxflags' : '/O2 /EHsc' }
    },
    # ==========================================================
    # === DEPS
    {
        'for' : { 'task' : 'util' },
        'not-for' : { 'platform' : 'windows' },
        'set' : {
            'sys-libs' : 'boost_timer',
        }
    },
    # Special case for boost on windows
    # This setup for boost installed on windows as C:\local\boost_1_67_0
    # For example, command 'choco install boost-msvc-14.1' produces such an installation.
    # To run program linked with boost dlls OS Windows needs to know path to dir
    # with boost dlls. In console it can be made like this:
    # set PATH=C:\local\boost_1_67_0\lib64-msvc-14.1;%PATH%
    {
        'for' : { 'task' : 'util', 'platform' : 'windows' },
        'set' : {
            'includes' : 'C:\\local\\boost_1_67_0',
            #'libpath' : 'C:\\local\\boost_1_67_0\\lib64-msvc-14.1',
            'libpath' : r'C:\local\boost_1_67_0\lib64-msvc-14.1',
        }
    },
    {
        'for' : { 'task' : 'util', 'platform' : 'windows', 'buildtype' : 'debug' },
        'set' : {
            'sys-libs' : 'boost_timer-vc141-mt-gd-x64-1_67',
        }
    },
    {
        'for' : { 'task' : 'util', 'platform' : 'windows', 'buildtype' : 'release' },
        'set' : {
            'sys-libs' : 'boost_timer-vc141-mt-x64-1_67',
        }
    },
    # ==========================================================
    # === CONFIGURATION TESTS
    {
        'for' : { 'task' : 'util' },
        'set' : {
            'conftests'  : [
                dict(act = 'check-headers', names = 'cmath iostream'),
                dict(act = 'check-sys-libs'),
            ],
        }
    },
]