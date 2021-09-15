
tasks = {
    'foo.luac' : {
        'source' : 'foo.lua',
        #'target' : 'foo.luac',
        'configure' : [ dict(do = 'find-program', names = 'luac'), ],
        'run': '${LUAC} -s -o $(tgt) $(src)',
    },
    # alternative way to do the same thing but with different target file name
    'foo2.luac' : {
        'source' : 'foo.lua',
        'configure' : [ dict(do = 'find-program', names = 'luac'), ],
        'run': '${LUAC} -s -o foo2.luac $(src)',
    },
    # one more alternative way to do the same thing but with different target file name
    'foo3.luac' : {
        'configure' : [ dict(do = 'find-program', names = 'luac'), ],
        'run': { 'cmd' : '${LUAC} -s -o $(tgt) foo.lua', 'cwd' : '.' },
    },
}
