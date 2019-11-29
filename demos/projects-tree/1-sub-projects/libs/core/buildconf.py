
def check():
    # some checking
    return True

startdir = 'src'

#project = { 'version' : '0.4.0' }

tasks = {
    'corelib' : {
        'features' : 'shlib',
        'source'   :  dict( include = '**/*.cpp' ),
        #'includes' : 'src',
        'export-includes' : True,
        'conftests'  : [
            check,
        ],
    },
}
