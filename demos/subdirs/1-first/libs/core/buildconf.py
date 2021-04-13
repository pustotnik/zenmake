
def check(**kwargs):
    # some checking
    return True

tasks = {
    'corelib' : {
        'features' : 'cshlib',
        'source'   : '**/*.c',
        'includes' : 'src',
        'export'   : 'includes',
        'ver-num' : '0.4.0',
        'configure'  : [
            dict(do = 'check-headers', names = 'stdio.h'),
            check,
        ],
    },
}

byfilter = [
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
