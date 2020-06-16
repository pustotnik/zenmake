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
absent or: ``task``, ``buildtype``. It's better to use `**kwargs` in this
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

    ``do`` = ``check-libs``
        *Parameters*: ``names`` = [], ``fromtask`` = True, ``defines`` = [],
        ``autodefine`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of the shared libraries from task
        parameter ``libs`` or/and from list in the ``names``.
        If ``fromtask`` is set to False then libraries from task
        parameter ``libs`` will not be used.
        If ``autodefine`` is set to True it generates
        C/C++ define name like ``HAVE_LIB_LIBNAME=1``.

        Parameter ``defines`` can be used to set additional C/C++ defines
        to use in compiling of the test.
        These defines will not be set for your code, only for the test.

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
        for your code when the test is over.

        Parameter ``defines`` can be used to set additional C/C++/D/Fortran defines
        to use in compiling of the test.
        These defines will not be set for your code, only for the test.

    ``do`` = ``check-programs``
        *Parameters*: ``names``, ``paths`` = [],  ``var`` = '', ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Check existence of programs from list in the ``names``.
        Parameter ``paths`` can be used to set paths to find
        these programs, but usually you don't need to use it.
        Parameter ``var`` can be used to set 'define' name.
        By default it's a first name from the ``names`` in upper case.

    ``do`` = ``call-pyfunc``
        *Parameters*: ``func``, ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Call a python function. It'a another way to use python
        function as an action. In this way you can use parameter
        ``mandatory``.

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
        ``call-pyfunc``, ``check-code``.

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