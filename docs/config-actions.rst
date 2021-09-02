.. include:: global.rst.inc
.. highlight:: python
.. _config-actions:

Configuration actions
=====================

ZenMake supports some configuration actions. They can be used to check system
libraries, headers, etc. To set configuration actions use the ``configure`` parameter
in :ref:`task params<buildconf-taskparams>`. The value of the ``configure`` parameter
must be a list of such actions. An item in the list
can be a ``dict`` where ``do`` specifies what to do, in other words it is some type of
configuration action. It's like a function where ``do`` describes the name of
a function and others parameters are parameters for the function.

There is another possible value for such an item in python format of buildconf file
and it is a python function which must return True/False on Success/Failure.
If such a function raises some exception then ZenMake interprets it
as if the function returns False. This function can be without arguments or
with named arguments: ``taskname``, ``buildtype``.
It's better to use `**kwargs` to have universal way to work with any input arguments.

These actions can be run sequentially or in parallel (see ``do`` = ``parallel``).
And they all are called on the **configure** step (in command **configure**).

Results of the same configuration actions are cached when it's possible
but not between runnings of ZenMake.

These configuration actions in ``dict`` format:

    ``do`` = ``check-headers``
        *Parameters*: ``names``, ``defname`` = '', ``defines`` = [],
        ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of C/C++ headers from the ``names`` list.

        The ``defname`` parameter is a name of a define to set
        for your code when the action is over. By default the name for each header
        is generated in the form 'HAVE_<HEADER NAME>=1'. For example, if you set
        'cstdio' in the ``names`` then the define 'HAVE_CSTDIO=1' will be generated.
        If you set 'stdio.h' in the ``names`` then the define 'HAVE_STDIO_H=1'
        will be generated.

        The ``defines`` parameter can be used to set additional C/C++ defines
        to use in compiling of the action.
        These defines will not be set for your code, only for the action.

        The :ref:`toolchain<buildconf-taskparams-toolchain>`,
        :ref:`includes<buildconf-taskparams-includes>`
        and :ref:`libpath<buildconf-taskparams-libpath>` task parameters
        affect this type of action.

    ``do`` = ``check-libs``
        *Parameters*: ``names`` = [], ``fromtask`` = True, ``defines`` = [],
        ``autodefine`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of the shared libraries from the ``libs`` task
        parameter or/and from the ``names`` list.
        If ``fromtask`` is set to False then names of libraries from the ``libs``
        task parameter will not be used for checking.
        If ``autodefine`` is set to True it generates
        C/C++ define name like ``HAVE_LIB_LIBNAME=1``.

        The ``defines`` parameter can be used to set additional C/C++ defines
        to use in compiling of the action.
        These defines will not be set for your code, only for the action.

        The :ref:`toolchain<buildconf-taskparams-toolchain>`,
        :ref:`includes<buildconf-taskparams-includes>`
        and :ref:`libpath<buildconf-taskparams-libpath>` task parameters
        affect this type of action.

    ``do`` = ``check-code``
        *Parameters*: ``text`` = '', ``file`` = '', ``label`` = '',
        ``defines`` = [],  ``defname`` = '', ``execute`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++, D, Fortran.

        Provide piece of code for the test. Code can be provided with
        the ``text`` parameter as a plane text or with the ``file`` parameter
        as a path to the file with a code. This path can be absolute or relative to
        the :ref:`startdir<buildconf-startdir>`. At least one of the
        ``text`` or ``file`` parameters must be set.

        The ``label`` parameter can be used to mark message of the test.
        If the ``execute`` parameter is True it means that the resulting binary
        will be executed and the result will have effect on the current configuration action.

        The ``defname`` parameter is a name of C/C++/D/Fortran define to set
        for your code when the test is over. There is no such a name by default.

        The ``defines`` parameter can be used to set additional C/C++/D/Fortran defines
        to use in compiling of the test.
        These defines will not be set for your code, only for the test.

        The :ref:`toolchain<buildconf-taskparams-toolchain>`,
        :ref:`includes<buildconf-taskparams-includes>`
        and :ref:`libpath<buildconf-taskparams-libpath>` task parameters
        affect this type of action.

    ``do`` = ``find-program``
        *Parameters*: ``names``, ``paths``,  ``var`` = '', ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Find a program.
        The ``names`` parameter must be used to specify one or more possible file
        names for the program. Do not add an extension for portability.
        This action does nothing if ``names`` is empty.

        The ``paths`` parameter can be used to set paths to find
        the program, but usually you don't need to use it because by default
        the ``PATH`` system environment variable is used. Also the Windows Registry
        is used on MS Windows if the program was not found.

        The ``var`` parameter can be used to set
        :ref:`dynamic substitution<buildconf-substitutions-dynamic>` variable name.
        By default it's a first name from the ``names`` in upper case and without
        symbols '-' and '.'.
        If this name is found in environment variables, ZenMake will use it instead of
        trying to find the program. Also this name can be used in parameter
        :ref:`run <buildconf-taskparams-run>` like this:

        in YAML format:

        .. code-block:: yaml

            foo.luac:
              source : foo.lua
              configure : [ { do: find-program, names: luac } ]
              # var 'LUAC' will be set in 'find-program' if 'luac' is found.
              run: '${LUAC} -s -o ${TGT} ${SRC}'

        in Python format:

        .. code-block:: python

            'foo.luac' : {
                'source' : 'foo.lua',
                'configure' : [ dict(do = 'find-program', names = 'luac'), ],
                # var 'LUAC' will be set in 'find-program' if 'luac' is found.
                'run': '${LUAC} -s -o ${TGT} ${SRC}',
            },

    ``do`` = ``find-file``
        *Parameters*: ``names``, ``paths``,  ``var`` = '', ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Find a file on file system.
        The ``names`` parameter must be used to specify one or more possible file
        names.
        This action does nothing if ``names`` is empty.

        The ``paths`` parameter must be used to set paths to find
        the file. Each path can be absolute or relative to
        the :ref:`startdir<buildconf-startdir>`.
        By default it's '.' which means :ref:`startdir<buildconf-startdir>`.

        The ``var`` parameter can be used to set
        :ref:`dynamic substitution<buildconf-substitutions-dynamic>` variable name.
        By default it's a first name from the ``names`` in upper case and without
        symbols '-' and '.'.

    ``do`` = ``call-pyfunc``
        *Parameters*: ``func``, ``mandatory`` = True.

        *Supported languages*: any but only in python format of buildconf file.

        Call a python function. It'a another way to use python
        function as an action.
        In this way you can use the ``mandatory`` parameter.

    ``do`` = ``pkgconfig``
        *Parameters*: ``toolname`` = 'pkg-config', ``toolpaths``,
        ``packages``, ``cflags`` = True, ``libs`` = True, ``static`` = False,
        ``defnames`` = True, ``def-pkg-vars``, ``tool-atleast-version``,
        ``pkg-version`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++.

        Execute ``pkg-config`` or compatible tool (for example ``pkgconf``) and
        use results. The ``toolname`` parameter can be used to set name of the
        tool and it is 'pkg-config' by default.
        The ``toolpaths`` parameter can be used to set
        paths to find the tool, but usually you don't need to use it.

        The ``packages`` parameter is required parameter to set one or more names of
        packages in database of pkg-config. Each such a package name can be used
        with '>', '<', '=', '<=' or '>=' to check version of a package.

        The parameters named ``cflags`` (default: True), ``libs`` = (default: True),
        ``static`` (default: False) are used to set corresponding command line
        parameters ``--cflags``, ``--libs``, ``--static`` for 'pkg-config' to
        get compiler/linker options. If ``cflags`` or ``libs`` is True then
        obtained compiler/linker options are used by ZenMake in a build task.
        Parameter ``static`` means forcing of static libraries and
        it is ignored if ``cflags`` and ``libs`` are False.

        The ``defnames`` parameter is used to set C/C++ defines. It can be True/False
        or ``dict``. If it's True then default names for defines will be used.
        If it's False then no defines will be used. If it's ``dict`` then keys
        must be names of used packages and values must be dicts with keys ``have``
        and ``version`` and values as names for defines. By default it's True.
        Each package can have 'HAVE_PKGNAME' and 'PKGNAME_VERSION' define
        where PKGNAME is a package name in upper case. And it's default patterns.
        But you can set custom defines. Name of 'PKGNAME_VERSION' is used only
        if ``pkg-version`` is True.

        The ``pkg-version`` parameter can be used to get 'define' with version of
        a package. It can be True of False. If it's True then 'define' will be set.
        If it's False then corresponding 'define' will not be set. It's False by default.
        This parameter will not set 'define' if ``defnames`` is False.

        The ``def-pkg-vars`` parameter can be used to set custom values of variables
        for 'pkg-config'. It must be ``dict`` where keys and values are names and
        values of these variables. ZenMake uses the command line option ``--define-variable``
        for this parameter. It's empty by default.

        The ``tool-atleast-version`` parameter can be used to check minimum version
        of selected tool (pkg-config).

        Examples in YAML format:

        .. code-block:: yaml

            # Elements like 'tasks' and other task params are skipped

            # ZenMake will check package 'gtk+-3.0' and set define 'HAVE_GTK_3_0=1'
            configure:
                - do: pkgconfig
                  packages: gtk+-3.0

            # ZenMake will check packages 'gtk+-3.0' and 'pango' and
            # will check 'gtk+-3.0' version > 1 and <= 100.
            # Before checking of packages ZenMake will check that 'pkg-config' version
            # is greater than 0.1.
            # Also it will set defines 'WE_HAVE_GTK3=1', 'HAVE_PANGO=1',
            # GTK3_VER="gtk3-ver" and LIBPANGO_VER="pango-ver" where 'gtk3-ver'
            # and 'pango-ver' are values of current versions of
            # 'gtk+-3.0' and 'pango'.
            configure:
                - do: pkgconfig
                  packages: 'gtk+-3.0 > 1 pango gtk+-3.0 <= 100'
                  tool-atleast-version: '0.1'
                  pkg-version: true
                  defnames:
                      gtk+-3.0: { have: WE_HAVE_GTK3, version: GTK3_VER }
                      pango: { version: LIBPANGO_VER }

        Examples in Python format:

        .. code-block:: python

            # Elements like 'tasks' and other task params are skipped

            # ZenMake will check package 'gtk+-3.0' and set define 'HAVE_GTK_3_0=1'
            'configure'  : [
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
            'configure'  : [
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
        ``args`` = '\-\-cflags \-\-libs', ``static`` = False,
        ``parse-as`` = 'flags-libs', ``defname``, ``var``, ``msg``,
        ``mandatory`` = True.

        *Supported languages*: any.

        Execute any ``*-config`` tool. It can be pkg-config, sdl-config,
        sdl2-config, mpicc, etc.

        ZenMake doesn't know which tool will be used and therefore this action
        can be used in any task including standalone runcmd task.

        The ``toolname`` parameter must be used to set name of such a tool.
        The ``toolpaths`` parameter can be used to set
        paths to find the tool, but usually you don't need to use it.

        The ``args`` parameter can be used to set command line arguments. By default
        it is '\-\-cflags \-\-libs'.

        The ``static`` parameter means forcing of static libraries and
        it is ignored if ``parse-as`` is not set to 'flags-libs'.

        The ``parse-as`` parameter describes how to parse output. If it is 'none'
        then output will not be parsed. If it is 'flags-libs' then ZenMake will
        try to parse the output for compiler/linker options but ZenMake knows how
        to parse C/C++ compiler/linker options only, other languages are not
        supported for this value. And if it is 'entire'
        then output will not be parsed but value of output will be set to define
        name from the ``defname`` and/or ``var`` if they are defined.
        By default ``parse-as`` is set to 'flags-libs'.

        The ``defname`` parameter can be used to set C/C++ define. If ``parse-as``
        is set to 'flags-libs' then ZenMake will try to set define name by using
        value of the ``toolname`` discarding '-config' part if it exists. For example
        if the ``toolname`` is 'sdl2-config' then 'HAVE_SDL2=1' will be used.
        For other values of ``parse-as`` there is no default value for ``defname``
        but you can set some custom define name.

        The ``var`` parameter can be used to set
        :ref:`dynamic substitution<buildconf-substitutions-dynamic>` variable name. This parameter
        is ignored if value of ``parse-as`` is not 'entire'.
        By default it is not defined.

        The ``msg`` parameter can be used to set custom message for this action.

        Examples in YAML format:

        .. code-block:: yaml

            tasks:
              myapp:
                # other task params are skipped
                configure:
                  # ZenMake will get compiler/linker options for SDL2 and
                  # set define to 'HAVE_SDL2=1'
                  - do: toolconfig
                    toolname: sdl2-config
                    # ZenMake will get SDL2 version and put it in the define 'SDL2_VERSION'
                  - do: toolconfig
                    toolname: sdl2-config
                    msg: Getting SDL2 version
                    args: --version
                    parse-as: entire
                    defname: SDL2_VERSION

        Examples in Python format:

        .. code-block:: python

            tasks = {
                'myapp' : {
                    # other task params are skipped
                    'configure'  : [
                        # ZenMake will get compiler/linker options for SDL2 and
                        # set define to 'HAVE_SDL2=1'
                        { 'do' : 'toolconfig', 'toolname' : 'sdl2-config' },
                        # ZenMake will get SDL2 version and put it in the define 'SDL2_VERSION'
                        {
                            'do' : 'toolconfig',
                            'toolname' : 'sdl2-config',
                            'msg' : 'Getting SDL2 version',
                            'args' : '--version',
                            'parse-as' : 'entire',
                            'defname' : 'SDL2_VERSION',
                        },
                    ]
                },
            }

    ``do`` = ``write-config-header``
        *Parameters*: ``file`` = '', ``guard`` = '',  ``remove-defines`` = True,
        ``mandatory`` = True.

        *Supported languages*: C, C++.

        Write a configuration header in the build directory after some
        configuration actions.
        By default file name is ``<task name>_config.h``.
        The ``guard`` parameter can be used to change C/C++ header guard.
        The ``remove-defines`` parameter means removing the defines after they are
        added into configuration header file and it is True by default.

        In your C/C++ code you can just include this file like that:

        .. code-block:: c++

            #include "yourconfig.h"

        You can override file name by using the ``file`` parameter.

    ``do`` = ``parallel``
        *Parameters*: ``actions``, ``tryall`` = False,  ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Run configuration actions from the ``actions`` parameter
        in parallel. Not all types of actions are supported.
        Allowed actions are ``check-headers``, ``check-libs``,
        ``check-code`` and ``call-pyfunc``.

        If you use ``call-pyfunc`` in ``actions`` you should understand that
        python function must be thread safe. If you don't use any shared data
        in such a function you don't need to worry about concurrency.

        If the ``tryall`` parameter is True then all configuration actions
        from the ``actions`` parameter will be executed despite of errors.
        By default the ``tryall`` is False.

        You can control order of the actions by using the parameters ``before``
        and ``after`` with the parameter ``id``. For example, one action can have
        ``id = 'base'`` and then another action can have ``after = 'base'``.

Any configuration action has the ``mandatory`` parameter which is True by default.
It also has effect for any action inside ``actions``
for parallel actions and for the whole bundle of parallel actions as well.

All results (defines and some other values) of configuration actions
(excluding ``call-pyfunc``) in one build
task can be exported to all dependent build tasks.
Use :ref:`export<buildconf-taskparams-export>` with the name `config-results`
for this ability. It allows you to avoid writing the same config actions in tasks
and reduce configuration actions time run.

Example in python format:

.. code-block:: python

    def check(**kwargs):
        buildtype = kwargs['buildtype']
        # some checking
        return True

    tasks = {
        'myapp' : {
            'features'   : 'cxxshlib',
            'libs'   : ['m', 'rt'],
            # ...
            'configure'  : [
                # do checking in function 'check'
                check,
                # Check libs from param 'libs'
                # { 'do' : 'check-libs' },
                { 'do' : 'check-headers', 'names' : 'cstdio', 'mandatory' : True },
                { 'do' : 'check-headers', 'names' : 'cstddef stdint.h', 'mandatory' : False },
                # Each lib will have define 'HAVE_LIB_<LIBNAME>' if autodefine = True
                { 'do' : 'check-libs', 'names' : 'pthread', 'autodefine' : True,
                            'mandatory' : False },
                { 'do' : 'find-program', 'names' = 'python' },
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
        },
    }
