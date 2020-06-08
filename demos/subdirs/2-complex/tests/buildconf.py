
tasks = {
    'testcmn' : {
        'features' : 'cxxshlib test',
        'source'   : 'src/test_common.cpp',
        'includes' : 'src',
    },
    'test.py' : {
        'features' : 'test',
        'run'      : {
            'cmd'   : 'python src/test.py',
            'cwd'   : '.',
            'env'   : { 'JUST_ENV_VAR' : 'qwerty', },
            'shell' : False,
        },
        'config-actions' : [ dict(do = 'check-programs', names = 'python'), ]
    },
}
