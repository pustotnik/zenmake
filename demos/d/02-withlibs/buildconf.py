
fragment1 = """
int main()
{
    return 0;
}
"""

fragment2 = """
import core.stdc.stdio;

int main()
{
    printf("fragment2\n");
    return 0;
}
"""

tasks = {
    'dll' : {
        #'features' : 'dshlib',
        'features' : 'shlib',
        'source'   : 'src/dll.d',
    },
    'staticlib' : {
        #'features' : 'dstlib',
        'features' : 'stlib',
        'source'   : 'src/static_lib.d',
    },
    'test' : {
        #'features' : 'dprogram',
        'features' : 'program',
        'source'   : 'src/main.d',
        'includes' : 'src',
        'use'      : 'staticlib dll',
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
        #'toolchain': 'auto-d',
        #'toolchain': 'ldc2',
        #'toolchain': 'dmd',
        #'toolchain': 'gdc',

        'dflags' : '-O',
    }
}

toolchains = {
    'gdc': {
        'LINKFLAGS' : '-pthread', # just as an example of linker flags
    },
}

