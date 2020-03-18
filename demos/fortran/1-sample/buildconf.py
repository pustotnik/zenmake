
fragment1 = """
program Empty
end program Empty
"""

fragment2 = """
program HelloWorld
    write (*,*) 'Hello, world!'
end program HelloWorld
"""

tasks = {
    'hello': {
        'features' : 'program',
        'source'   : 'src/hello.f90',
    },
    'sharedlib' : {
        #'features' : 'fcshlib',
        'features' : 'shlib',
        'source'   : 'src/funcs.f90',
    },
    'staticlib' : {
        #'features' : 'fcstlib',
        'features' : 'stlib',
        'source'   : 'src/funcs2.f90',
    },
    'test' : {
        'features' : 'fcprogram',
        #'features' : 'program',
        'source'   : 'src/calculator.f90 src/main.f90',
        'includes' : 'src/inc',
        'use'      : 'staticlib sharedlib',
        'conftests'  : [
            dict( act = 'parallel',
                checks = [
                    dict(act = 'check-code', text = fragment1, label = 'fragment1'),
                    dict(act = 'check-code', text = fragment2, label = 'fragment2', execute = True)
                ],
            ),
        ],
    },
}

buildtypes = {
    'release' : {
        #'toolchain': 'auto-fc',
        #'toolchain': 'gfortran',

        'fcflags.select' : {
            'windows ifort': '/O2',
            'default': '-O2',
        },
        'rpath' : '.',
    },
}

toolchains = {
    'gfortran': {
        'FCFLAGS' : '-Wall -W',
    },
    'ifort': {
        'FCFLAGS' : '-warn',
    },
}