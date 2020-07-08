
zmdepdir = '../../../zmdep-a'
dependencies = {
    'zmdep-a' : {
        'rootdir': zmdepdir,
        'export-includes' : zmdepdir,
    },
}

tasks = {
    'core' : {
        'features' : 'cxxshlib',
        'source'   : '**/*.cpp',
        'ver-num'  : '0.2.0',
        'use' : 'zmdep-a:calclib zmdep-a:printlib',
    },
}

