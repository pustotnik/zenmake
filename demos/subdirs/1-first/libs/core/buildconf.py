
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
        'for' : 'all',
        'set' : {
            'toolchain.select': {
                'default': 'gcc',
                'darwin' : 'clang',
                'windows': 'msvc',
            }
        }
    },
]
