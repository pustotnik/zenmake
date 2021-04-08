
# Based on demos/dbus from Waf
tasks = {
    'test' : {
        'configure' : [ dict(do = 'find-program', names = 'dbus-binding-tool', var = 'DBUS_BINDING_TOOL'), ],
        'target' : 'test.h',
        'source' : 'test.xml',
        'run': {
            'cmd' : "${DBUS_BINDING_TOOL} --prefix=test_prefix --mode=glib-server --output=${TGT} ${SRC}",
            'shell' : True,
        }
    },
    'hello' : {
        'features': 'cprogram',
        'source' : '*.c',
        #'includes' : '/usr/include/glib-2.0 /usr/lib/glib-2.0/include /usr/include/dbus-1.0',
        'use': 'test',
    },
}
