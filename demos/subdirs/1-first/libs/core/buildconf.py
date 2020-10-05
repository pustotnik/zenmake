
def check(**kwargs):
    # some checking
    return True

tasks = {
    'corelib' : {
        'features' : 'cshlib',
        'source'   : '**/*.c',
        'includes' : 'src',
        'export-includes' : True,
        'ver-num' : '0.4.0',
        'config-actions'  : [
            dict(do = 'check-headers', names = 'stdio.h'),
            check,
        ],
    },
}

matrix = [
    {
        'for' : { 'buildtype' : ['debug-gcc', 'release-gcc'], },
        'set' : {
            'toolchain' : 'gcc',
        }
    },
    {
        'for' : { 'buildtype' : ['debug-clang', 'release-clang'], },
        'set' : {
            'toolchain' : 'clang',
        }
    },
]
