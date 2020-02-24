.. include:: global.rst.inc
.. highlight:: python
.. _conftests:

Configuration tests
===================

ZenMake supports some configuration tests. They can be used to check system
libraries, headers, etc. To set configuration tests the parameter ``conftests``
in :ref:`task params<buildconf-taskparams>` is used. The value of the parameter
``conftests`` must be a list of configuration tests. An item in the list
can be a ``dict`` where ``act`` specifies some type of configuration test.

Another possible value of the item is a python function that must return
True/False on Success/Failure. If this function raise some exception then it
means the function returns False. Arguments for such a function can be
absent or: ``task``, ``buildtype``. It's better to use `**kwargs` in this
function to have universal way to work with any input arguments.

These tests can be run sequentially or in parallel (see ``act`` = ``parallel``).
And they all are called on **configure** step (command **configure**).

When it's possible results of the same configuration tests are cached
but not between runnings of ZenMake.

These configuration tests in ``dict`` format:

    ``act`` = ``check-headers``
        *Parameters*: ``names``, ``defines`` = [],  ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of C/C++ headers from list in the ``names``.

        Parameter ``defines`` can be used to set additional C/C++ defines
        to use in compiling of the test.

    ``act`` = ``check-libs``
        *Parameters*: ``names``, ``defines`` = [],  ``autodefine`` = False,
        ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of the system libraries from list in
        the ``names``. If ``autodefine`` is set to True it generates
        C/C++ define name like ``HAVE_LIB_SOMELIB``.

        Parameter ``defines`` can be used to set additional C/C++ defines
        to use in compiling of the test.

    ``act`` = ``check-sys-libs``
        *Parameters*: ``defines`` = [],  ``autodefine`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++.

        Check existence of all system libraries from
        task parameter ``sys-libs``. All parameters for the act ``check-libs``
        excluding ``names`` can be used here.

    ``act`` = ``check-code``
        *Parameters*: ``text`` = '', ``file`` = '', ``label`` = '',
        ``defines`` = [],  ``defname`` = '', ``execute`` = False, ``mandatory`` = True.

        *Supported languages*: C, C++, D.

        Provide piece of code for the test. Code can be provided with
        parameter ``text`` as a plane text or with parameter ``file`` as a path to
        file with code. This path can be absolute or relative to
        the :ref:`startdir<buildconf-startdir>`. At least one of the
        parameters ``text`` or ``file`` must be set.

        Parameter ``label`` can be used to mark message of the test.
        If parameter ``execute`` is True it means that the resulting binary
        will be executed.

        Parameter ``defname`` is a name of C/C++ define to set
        when the test is over.

        Parameter ``defines`` can be used to set additional C/C++ defines
        to use in compiling of the test.

    ``act`` = ``check-programs``
        *Parameters*: ``names``, ``paths`` = [],  ``var`` = '', ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Check existence of programs from list in the ``names``.
        Parameter ``paths`` can be used to set paths to find
        these programs, but usually you don't need to use it.
        Parameter ``var`` can be used to set 'define' name.
        By default it's a first name from the ``names`` in upper case.

    ``act`` = ``check-by-pyfunc``
        *Parameters*: ``func``, ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Check by python function. It'a another way to use python
        function for checking. In this way you can use parameter
        ``mandatory``.

    ``act`` = ``write-config-header``
        *Parameters*: ``file`` = '', ``guard`` = '',  ``mandatory`` = True.

        *Supported languages*: C, C++.

        After all the configuration tests are executed, write a
        configuration header in the build directory.
        The configuration header is used to limit the size of the
        command-line. By default file name is ``<task name>_config.h``.
        Parameter ``guard`` can be used to change C/C++ header guard.
        In your C/C++ code you can just include this file like that:

        .. code-block:: c++

            #include "yourconfig.h"

        You can override file name by using parameter ``file``.

    ``act`` = ``parallel``
        *Parameters*: ``checks``, ``tryall`` = False,  ``mandatory`` = True.

        *Supported languages*: all languages supported by ZenMake.

        Run configuration tests from the parameter ``checks``
        in parallel. Not all types of tests are supported.
        Allowed tests are ``check-sys-libs``, ``check-headers``,
        ``check-libs``, ``check-by-pyfunc``.

        If you use ``check-by-pyfunc`` in ``checks`` you should understand that
        python function must be thread safe. If you don't use any shared data
        in such a function you don't need to worry about concurrency.

        If parameter ``tryall`` is True then all configuration tests
        from the parameter ``checks`` will be executed despite of errors.
        By default the ``tryall`` is False.

        You can control order of tests here by using parameters ``before``
        and ``after`` with a parameter ``id``. For example, one test can have
        ``id = 'base'`` and then another test can have ``after = 'base'``.

Any configuration test has parameter ``mandatory`` which is True by default.
It also has effect for any test inside ``checks``
for parallel tests and for the whole bundle of parallel tests as well.

Example in python format:

.. code-block:: python

    def check(**kwargs):
        task = kwargs['task']
        buildtype = kwargs['buildtype']
        # some checking
        return True

    'myapp' : {
        'features'   : 'cxxshlib',
        'sys-libs'   : ['m', 'rt'],
        # ...
        'conftests'  : [
            # do checking in function 'check'
            check,
            # Check libs from param 'sys-libs'
            #dict(act = 'check-sys-libs'),
            dict(act = 'check-headers', names = 'cstdio', mandatory = True),
            dict(act = 'check-headers', names = 'cstddef stdint.h', mandatory = False),
            # Each lib will have define 'HAVE_LIB_<LIBNAME>' if autodefine = True
            dict(act = 'check-libs', names = 'pthread', autodefine = True,
                        mandatory = False),
            dict(act = 'check-programs', names = 'python'),
            dict( act = 'parallel',
                checks = [
                    dict(act = 'check-sys-libs', id = 'syslibs'),
                    dict(act = 'check-headers', names = 'stdlib.h iostream'),
                    dict(act = 'check-headers', names = 'stdlibasd.h', mandatory = False),
                    dict(act = 'check-headers', names = 'string', after = 'syslibs'),
                ],
                mandatory = False,
                #tryall = True,
            ),

            #dict(act = 'write-config-header', file = 'myapp_config.h')
            dict(act = 'write-config-header'),
        ],
    }
