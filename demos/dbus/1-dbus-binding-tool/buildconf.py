
# Based on demos/dbus from Waf
tasks = {
    'test' : {
        'conftests' : [ dict(act = 'check-programs', names = 'dbus-binding-tool', var = 'DBUS_BINDING_TOOL'), ],
        'target' : 'test.h',
        'source' : 'test.xml',
        'run': {
            'cmd' : "${DBUS_BINDING_TOOL} --prefix=test_prefix --mode=glib-server --output=${TGT} ${SRC}",
            'shell' : True,
        }
    },
    'hello' : {
        'features': 'program',
        'source' : dict( include = '*.c' ),
        #'includes' : '/usr/include/glib-2.0 /usr/lib/glib-2.0/include /usr/include/dbus-1.0',
        'use': 'test',
    },
}
