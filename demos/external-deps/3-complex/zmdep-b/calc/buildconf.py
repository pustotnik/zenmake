
tasks = {
    'calc' : {
        'features' : 'cshlib',
        'source'   :  dict( include = '**/*.c' ),
        'includes' : '..',
        'ver-num'  : '0.2.5',
        'use' : 'zmdep-a:calclib',
    },
}

