
def check():
    import sys
    return sys.maxsize >= 4**21

tasks = {
    'asmtest' : {
        'features'    : 'asmprogram',
        'source'      : 'test.s',
        'asflags'     : '-f elf64',
        'aslinkflags' : '-s',
        'toolchain'   : 'nasm',
        'configure' : [
            check,
            { 'do' : 'find-program', 'names' : 'ld', 'var' : 'ASLINK' },
        ],
    },
}
