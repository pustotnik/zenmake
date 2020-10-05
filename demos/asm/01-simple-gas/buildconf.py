
def check(**kwargs):
    import sys
    return sys.maxsize >= 4**21

tasks = {
    'asmtest' : {
        'features'  : 'asm cprogram',
        'source'    : 'main.c test.S',
        'defines'   : 'foo=12',
        'asflags'   : '-Os',
        'toolchain' : 'gcc gas',
        'config-actions' : [
            #{ 'do' : 'call-pyfunc', 'func' : check, 'mandatory': False  },
            check,
        ],
    },
}
