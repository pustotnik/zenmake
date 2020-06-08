
def check():
    import sys
    try:
        size = sys.maxint
    except AttributeError:
        size = sys.maxsize # python >= 3.2
    return size >= 4**21

tasks = {
    'asmtest' : {
        'features'    : 'asmprogram',
        'source'      : 'test.s',
        'asflags'     : '-f elf64',
        'aslinkflags' : '-s',
        'toolchain'   : 'nasm',
        'config-actions'   : [
            check,
            { 'do' : 'check-programs', 'names' : 'ld', 'var' : 'ASLINK' },
        ],
    },
}
