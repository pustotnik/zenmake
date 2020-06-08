
tasks = {
    'foo.luac' : {
        'source' : 'foo.lua',
        #'target' : 'foo.luac',
        'config-actions' : [ dict(do = 'check-programs', names = 'luac'), ],
        'run': '${LUAC} -s -o ${TGT} ${SRC}',
    },
    # alternative way to do the same thing but with different target file name
    'foo2.luac' : {
        'source' : 'foo.lua',
        'config-actions' : [ dict(do = 'check-programs', names = 'luac'), ],
        'run': '${LUAC} -s -o foo2.luac ${SRC}',
    },
    # one more alternative way to do the same thing but with different target file name
    'foo3.luac' : {
        'config-actions' : [ dict(do = 'check-programs', names = 'luac'), ],
        'run': { 'cmd' : '${LUAC} -s -o ${TARGET} foo.lua', 'cwd' : '.' },
    },
}
