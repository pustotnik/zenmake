.. include:: global.rst.inc
.. _buildtests:

Tests
============

ZenMake supports building and running tests. It has not special support for
particular testing framework/library but it can be any testing
framework/library.

To set up test you need to specify task feature ``test`` in ``buildconf`` file.
Then you have a choice:

    - If selected task has feature \*program then you may not need to do
      anything more. ZenMake wil try to build/run this task as test as is.
      But you can specify task parameter :ref:`run <buildconf-taskparams-run>`
      to set up additional arguments.

    - If selected task has no feature \*program and has no
      :ref:`run <buildconf-taskparams-run>` but has \*stlib/\*shlib then
      this task is cosidered as a task with test but ZenMake will not try
      to run this task as test. It's useful for creation of separated
      libraries for tests only.

    - Specify task parameter :ref:`run <buildconf-taskparams-run>`.

Tests are always built only on ``build`` stage and run only on ``test`` stage.
Order of buiding and running test tasks is controlled by their depedencies
as for just build tasks. So it's possible to use task parameter ``use`` to
control order of running of tests.

    Example of test tasks in python format:

    .. code-block:: python

        'stlib-test' : {
            'features' : 'cxxprogram test',
            'source'   : 'tests/test_stlib.cpp',
            # testcmn here is some library with common code for tests
            'use'      : 'stlib testcmn',
        },

        'test from script' : {
            'features' : 'test',
            'run'      : {
                'cmd'     : 'python tests/test.py',
                'cwd'     : '.',
                'shell'   : False,
            },
            'use'       : 'complex',
            'conftests' : [ dict(act = 'check-programs', names = 'python'), ]
        },
        # testcmn is a library with common code for tests only
        'testcmn' : {
            'features' : 'cxxshlib test',
            'source'   :  'tests/common.cpp',
            'includes' : '.',
        },
        'shlib-test' : {
            'features'    : 'cxxprogram test',
            'source'      : 'tests/test_shlib.cpp',
            'use'         : 'shlib testcmn',
            'run'      : {
                'cmd'     : '${PROGRAM} a b c',
                'env'     : { 'AZ' : '111', 'BROKEN_TEST' : 'false'},
                'repeat'  : 2,
                'timeout' : 10, # in seconds, Python 3 only
                'shell'   : False,
            },
        },
        'shlibmain-test' : {
            'features'    : 'cxxprogram test',
            'source'      : 'tests/test_shlibmain.cpp',
            'use'         : 'shlibmain testcmn',
        },

Use can build and/or run tests with command ``test``. You can do it with
command ``build`` as well but ``build`` doesn't do it by default, only if some
command line arguments are used.

To build and run all tests with command ``test``:

.. code-block:: console

    zenmake test

The same action with command ``build``:

.. code-block:: console

    zenmake build -t yes -T all

To build but not run tests with command ``test``:

.. code-block:: console

    zenmake test -T none

You can run all tests but also you can tests only on changes. For this you can
use ``--run-tests`` with value ``on-changes``:

.. code-block:: console

    zenmake test -T on-changes
