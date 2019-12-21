
def check(**kwargs):
    import sys
    try:
        size = sys.maxint
    except AttributeError:
        size = sys.maxsize # python >= 3.2
    return size >= 4**21

tasks = {
    'asmtest' : {
        'features'  : 'program',
        'source'    : 'main.c test.S',
        'defines'   : 'foo=12',
        'asflags'   : '-Os',
        'toolchain' : 'gcc gas',
        'conftests' : [
            #{ 'act' : 'check-by-pyfunc', 'func' : check, 'mandatory': False  },
            check,
        ],
    },
}
