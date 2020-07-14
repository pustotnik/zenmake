.. include:: global.rst.inc
.. highlight:: python
.. _config-actions:

Configuration actions
=====================

ZenMake supports some configuration actions. They can be used to check system
libraries, headers, etc. To set configuration actions the parameter ``config-actions``
in :ref:`task params<buildconf-taskparams>` is used. The value of the parameter
``config-actions`` must be a list of such actions. An item in the list
can be a ``dict`` where ``do`` specifies what to do, some type of
configuration action. It's like a function where ``do`` describes the name of
a function and others parameters are parameters for the function.

Another possible value of the item is a python function that must return
True/False on Success/Failure. If this function raise some exception then it
means the function returns False. Arguments for such a function can be
absent or: ``taskname``, ``buildtype``. It's better to use `**kwargs` in this
function to have universal way to work with any input arguments.

These actions can be run sequentially or in parallel (see ``do`` = ``parallel``).
And they all are called on **configure** step (command **configure**).

When it's possible results of the same configuration actions are cached
but not between runnings of ZenMake.

These configuration actions in ``dict`` format:

    ``do`` = ``check-headers``
        *Parameters*: ``names``, ``defname`` = '', ``defines`` = [],
        ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of C/C++ headers from list in the ``names``.

        Parameter ``defname`` is a name of a define to set
        for your code when the test is over. By default the name for each header
        is generated in the form 'HAVE_<HEADER NAME>=1'. For example, if you set
        'cstdio' in the ``names`` then the define 'HAVE_CSTDIO=1' will be generated.
        If you set 'stdio.h' in the ``names`` then the define 'HAVE_STDIO_H=1'
        will be generated.

        Parameter ``defines`` can be used to set additional C/C++ defines
        to use in compiling of the test.
        These defines will not be set for your code, only for the test.

        Task parameters :ref:`toolchain<buildconf-taskparams-toolchain>`,
        :ref:`includes<buildconf-taskparams-includes>`
        and :ref:`libpath<buildconf-taskparams-libpath>` affect this type of action.

    ``do`` = ``check-libs``
        *Parameters*: ``names`` = [], ``fromtask`` = True, ``defines`` = [],
        ``autodefine`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of the shared libraries from task
        parameter ``libs`` or/and from list in the ``names``.
        If ``fromtask`` is set to False then names of libraries from task
        parameter ``libs`` will not be used to check.
        If ``autodefine`` is set to True it generates
        C/C++ define name like ``HAVE_LIB_LIBNAME=1``.

        Parameter ``defines`` can be used to set additional C/C++ defines
        to use in compiling of the test.
        These defines will not be set for your code, only for the test.

        Task parameters :ref:`toolchain<buildconf-taskparams-toolchain>`,
        :ref:`includes<buildconf-taskparams-includes>`
        and :ref:`libpath<buildconf-taskparams-libpath>` affect this type of action.

    ``do`` = ``check-code``
        *Parameters*: ``text`` = '', ``file`` = '', ``label`` = '',
        ``defines`` = [],  ``defname`` = '', ``execute`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++, D, Fortran.

        Provide piece of code for the test. Code can be provided with
        parameter ``text`` as a plane text or with parameter ``file`` as a path to
        file with code. This path can be absolute or relative to
        the :ref:`startdir<buildconf-startdir>`. At least one of the
        parameters ``text`` or ``file`` must be set.

        Parameter ``label`` can be used to mark message of the test.
        If parameter ``execute`` is True it means that the resulting binary
        will be executed.

        Parameter ``defname`` is a name of C/C++/D/Fortran define to set
        for your code when the test is over. There is no such a name by default.

        Parameter ``defines`` can be used to set additional C/C++/D/Fortran defines
        to use in compiling of the test.
        These defines will not be set for your code, only for the test.

        Task parameters :ref:`toolchain<buildconf-taskparams-toolchain>`,
        :ref:`includes<buildconf-taskparams-includes>`
        and :ref:`libpath<buildconf-taskparams-libpath>` affect this type of action.

    ``do`` = ``check-programs``
        *Parameters*: ``names``, ``paths``,  ``var`` = '', ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Check existence of programs from list in the ``names``.
        Parameter ``paths`` can be used to set paths to find
        these programs, but usually you don't need to use it.
        Parameter ``var`` can be used to set
        :ref:`substitution<buildconf-substitutions>` variable name.
        By default it's a first name from the ``names`` in upper case.
        If this name is found in enviroment then ZenMake will use it instead of
        trying to find selected program. Also this name can be used in parameter
        :ref:`run <buildconf-taskparams-run>` like this:

        .. code-block:: python

            'foo.luac' : {
                'source' : 'foo.lua',
                'config-actions' : [ dict(do = 'check-programs', names = 'luac'), ],
                # var 'LUAC' will be set in 'check-programs' if 'luac' is found.
                'run': '${LUAC} -s -o ${TGT} ${SRC}',
            },

    ``do`` = ``call-pyfunc``
        *Parameters*: ``func``, ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Call a python function. It'a another way to use python
        function as an action. In this way you can use parameter
        ``mandatory``.

    ``do`` = ``pkgconfig``
        *Parameters*: ``toolname`` = 'pkg-config', ``toolpaths``,
        ``packages``, ``cflags`` = True, ``libs`` = True, ``static`` = False,
        ``defnames`` = True, ``def-pkg-vars``, ``tool-atleast-version``,
        ``pkg-version`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++.

        Execute ``pkg-config`` or compatible tool (for example ``pkgconf``) and
        use results. Parameter ``toolname`` can be used to set name of tool and
        it's 'pkg-config' by default. Parameter ``toolpaths`` can be used to set
        paths to find the tool, but usually you don't need to use it.

        Parameter ``packages`` is required parameter to set one or more names of
        packages in database of pkg-config. Each such a package name can be used
        with '>', '<', '=', '<=' or '>=' to check version of a package.

        Parameters ``cflags`` (default: True), ``libs`` = (default: True),
        ``static`` (default: False) are used to set corresponding command line
        parameters ``--cflags``, ``--libs``, ``--static`` for 'pkg-config' to
        get compiler/linker options. If ``cflags`` or ``libs`` is True then
        obtained compiler/linker options are used by ZenMake in a build task.
        Parameter ``static`` means forcing of static libraries and
        it is ignored if ``cflags`` and ``libs`` are False.

        Parameter ``defnames`` is used to set C/C++ defines. It can be True/False
        or ``dict``. If it's True then default names for defines will be used.
        If it's False then no defines will be used. If it's ``dict`` then keys
        must be names of used packages and values must be dicts with keys ``have``
        and ``version`` and values as names for defines. By default it's True.
        Each package can have 'HAVE_PKGNAME' and 'PKGNAME_VERSION' define
        where PKGNAME is a package name in upper case. And it's default patterns.
        But you can set custom defines. Name of 'PKGNAME_VERSION' is used only
        if ``pkg-version`` is True.

        Parameter ``pkg-version`` can be used to get define with version of
        a package. It can be True of False. If it's True then define will be set.
        If it's False then define will not be set. It's False by default.
        This parameter will not set define if ``defnames`` is False.

        Parameter ``def-pkg-vars`` can be used to set custom values of variables
        for 'pkg-config'. It must be ``dict`` where keys and values are names and
        values of these variables. ZenMake uses command line option ``--define-variable``
        for this parameter. It's empty by default.

        Parameter ``tool-atleast-version`` can be used to check minimum version
        of selected tool (pkg-config).

        Examples in Python format:

        .. code-block:: python

            # ZenMake will check package 'gtk+-3.0' and set define 'HAVE_GTK_3_0=1'
            'config-actions'  : [
                { 'do' : 'pkgconfig', 'packages' : 'gtk+-3.0' },
            ]

            # ZenMake will check packages 'gtk+-3.0' and 'pango' and
            # will check 'gtk+-3.0' version > 1 and <= 100.
            # Before checking of packages ZenMake will check that 'pkg-config' version
            # is greater than 0.1.
            # Also it will set defines 'WE_HAVE_GTK3=1', 'HAVE_PANGO=1',
            # GTK3_VER="gtk3-ver" and LIBPANGO_VER="pango-ver" where 'gtk3-ver'
            # and 'pango-ver' are values of current versions of
            # 'gtk+-3.0' and 'pango'.
            'config-actions'  : [
                {
                    'do' : 'pkgconfig',
                    'packages' : 'gtk+-3.0 > 1 pango gtk+-3.0 <= 100 ',
                    'tool-atleast-version' : '0.1',
                    'pkg-version' : True,
                    'defnames' : {
                        'gtk+-3.0' : { 'have' : 'WE_HAVE_GTK3', 'version': 'GTK3_VER' },
                        'pango' : { 'version': 'LIBPANGO_VER' },
                    },
                },
            ],

    ``do`` = ``toolconfig``
        *Parameters*: ``toolname`` = 'pkg-config', ``toolpaths``,
        ``args`` = '\\-\\-cflags \\-\\-libs', ``static`` = False,
        ``parse-as`` = 'flags-libs', ``defname``, ``msg``,
        ``mandatory`` = True.

        *Supported languages*: C, C++.

        Execute any ``*-config`` tool. It can be pkg-config, sdl-config,
        sdl2-config, mpicc, etc.

        Parameter ``toolname`` must be used to set name of such a tool.
        Parameter ``toolpaths`` can be used to set
        paths to find the tool, but usually you don't need to use it.

        Parameter ``args`` can be used to set command line arguments. By default
        it is '\\-\\-cflags \\-\\-libs'.

        Parameter ``static`` means forcing of static libraries and
        it is ignored if ``parse-as`` is not set to 'flags-libs'.

        Parameter ``parse-as`` describes how to parse output. If it is 'none'
        then output will not be parsed. If it is 'flags-libs' then ZenMake will
        try to parse the output for compiler/linker options. And if it is 'entire'
        then output will not be parsed but value of output will be set to define
        name from parameter ``defname``.
        By default ``parse-as`` is set to 'flags-libs'.

        Parameter ``defname`` can be used to set C/C++ define. If ``parse-as``
        is set to 'flags-libs' then ZenMake will try to set define name by using
        value of ``toolname`` discarding '-config' part if it exists. For example
        if ``toolname`` is 'sdl2-config' then 'HAVE_SDL2=1' will be used.
        For other values of ``parse-as`` there is no default value for ``defname``
        but you can set some custom define name.

        Parameter ``msg`` can be used to set custom message for this action.

        Examples in Python format:

        .. code-block:: python

            'config-actions'  : [
                # ZenMake will get compiler/linker options for SDL2 and set define 'HAVE_SDL2=1'
                { 'do' : 'toolconfig', 'toolname' : 'sdl2-config' },
                # ZenMake will get SDL2 version and set it in the define 'SDL2_VERSION'
                {
                    'do' : 'toolconfig',
                    'toolname' : 'sdl2-config',
                    'msg' : 'Getting SDL2 version',
                    'args' : '--version',
                    'parse-as' : 'entire',
                    'defname' : 'SDL2_VERSION',
                },
            ]


    ``do`` = ``write-config-header``
        *Parameters*: ``file`` = '', ``guard`` = '',  ``remove-defines`` = True,
        ``mandatory`` = True.

        *Supported languages*: C, C++.

        After some configuration actions are executed, write a
        configuration header in the build directory.
        The configuration header is used to limit the size of the
        command-line. By default file name is ``<task name>_config.h``.
        Parameter ``guard`` can be used to change C/C++ header guard.
        Parameter ``remove-defines`` means removing the defines after they are
        added into configuration header file and it is True by default.

        In your C/C++ code you can just include this file like that:

        .. code-block:: c++

            #include "yourconfig.h"

        You can override file name by using parameter ``file``.

    ``do`` = ``parallel``
        *Parameters*: ``actions``, ``tryall`` = False,  ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Run configuration actions from the parameter ``actions``
        in parallel. Not all types of actions are supported.
        Allowed actions are ``check-headers``, ``check-libs``,
        ``check-code`` and ``call-pyfunc``.

        If you use ``call-pyfunc`` in ``actions`` you should understand that
        python function must be thread safe. If you don't use any shared data
        in such a function you don't need to worry about concurrency.

        If parameter ``tryall`` is True then all configuration actions
        from the parameter ``actions`` will be executed despite of errors.
        By default the ``tryall`` is False.

        You can control order of actions here by using parameters ``before``
        and ``after`` with a parameter ``id``. For example, one action can have
        ``id = 'base'`` and then another action can have ``after = 'base'``.

Any configuration action has parameter ``mandatory`` which is True by default.
It also has effect for any action inside ``actions``
for parallel actions and for the whole bundle of parallel actions as well.

All results (defines and some other values) of configuration actions
(excluding ``call-pyfunc``) in one build
task can be exported to all build tasks which depend on the current task.
Use :ref:`export-config-actions<buildconf-taskparams-export-config-actions>`
for this ability. It allows you to avoid writing the same config actions in tasks
and reduce configuration actions time run.

Example in python format:

.. code-block:: python

    def check(**kwargs):
        buildtype = kwargs['buildtype']
        # some checking
        return True

    'myapp' : {
        'features'   : 'cxxshlib',
        'libs'   : ['m', 'rt'],
        # ...
        'config-actions'  : [
            # do checking in function 'check'
            check,
            # Check libs from param 'libs'
            # { 'do' : 'check-libs' },
            { 'do' : 'check-headers', 'names' : 'cstdio', 'mandatory' : True },
            { 'do' : 'check-headers', 'names' : 'cstddef stdint.h', 'mandatory' : False },
            # Each lib will have define 'HAVE_LIB_<LIBNAME>' if autodefine = True
            { 'do' : 'check-libs', 'names' : 'pthread', 'autodefine' : True,
                        'mandatory' : False },
            { 'do' : 'check-programs', 'names' = 'python' },
            { 'do' : 'parallel',
                'actions' : [
                    { 'do' : 'check-libs', 'id' : 'syslibs' },
                    { 'do' : 'check-headers', 'names' : 'stdlib.h iostream' },
                    { 'do' : 'check-headers', 'names' : 'stdlibasd.h', 'mandatory' : False },
                    { 'do' : 'check-headers', 'names' : 'string', 'after' : 'syslibs' },
                ],
                'mandatory' : False,
                #'tryall' : True,
            },

            #{ 'do' : 'write-config-header', 'file' : 'myapp_config.h' }
            { 'do' : 'write-config-header' },
        ],
    }
