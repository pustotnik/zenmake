
tasks = {
    'foo.luac' : {
        'source' : 'foo.lua',
        #'target' : 'foo.luac',
        'conftests' : [ dict(act = 'check-programs', names = 'luac'), ],
        'run': { 'cmd' : '${LUAC} -s -o ${TGT} ${SRC}' },
    },
    # alternative way to do the same thing but with different target file name
    'foo2.luac' : {
        'source' : 'foo.lua',
        'conftests' : [ dict(act = 'check-programs', names = 'luac'), ],
        'run': { 'cmd' : '${LUAC} -s -o foo2.luac ${SRC}' },
    },
    # one more alternative way to do the same thing but with different target file name
    'foo3.luac' : {
        'conftests' : [ dict(act = 'check-programs', names = 'luac'), ],
        'run': { 'cmd' : '${LUAC} -s -o ${TARGET} foo.lua', 'cwd' : '.' },
    },
}
