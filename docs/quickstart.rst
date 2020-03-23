.. include:: global.rst.inc
.. highlight:: bash
.. _quickstart:

Quickstart guide
================

To use ZenMake you need :ref:`ZenMake<installation>` and
:ref:`buildconf<buildconf>` file in the root of your project.

Let's consider an example with this structure::

    testproject
    ├── buildconf.py
    ├── prog
    │   └── test.cpp
    └── shlib
        ├── util.cpp
        └── util.h

For this project ``buildconf.py`` can be like that:

.. code-block:: python
   :linenos:

    tasks = {
        'util' : {
            'features' : 'shlib',
            'source'   :  { 'include' : 'shlib/**/*.cpp' },
            'includes' : '.',
        },
        'program' : {
            'features' : 'program',
            'source'   :  { 'include' : 'prog/**/*.cpp' },
            'includes' : '.',
            'use'      : 'util',
        },
    }

    buildtypes = {
        'debug' : {
            'toolchain' : 'auto-c++',
        },
        'release' : {
            'toolchain' : 'g++',
            'cxxflags'  : '-O2',
        },
        'default' : 'debug',
    }

=====  =======================================================================
Lines  Description
=====  =======================================================================
1      Section with build tasks
2,7    Names of build tasks. By default they are used as target names.
       Resulting target names will be adjusted depending on a platform.
       For example, on Windows 'program' will result to 'program.exe'.
3      Mark build task as a shared library.
4      Specify all \*.cpp files in the directory 'shlib' recursively.
5,10   Specify the path for C/C++ headers relative to the project root directory.
       In this example, this parameter is optional as ZenMake adds the
       project root directory itself. But it's an example.
8      Mark build task as an executable.
9      Specify all \*.cpp files in the directory 'prog' recursively.
11     Specify task 'util' as dependency to task 'program'.
15     Section with build types.
16,19  Names of build types. They can be almost any.
17     Specify auto detecting system C++ compiler.
20     Specify g++ compiler (from gcc).
21     Specify C++ compiler flags.
23     Special case: specify default build type that is used when no build
       type was specified for ZenMake command.
=====  =======================================================================

In case of using YAML the file ``buildconf.yaml`` with the same values as above
would look like this:

.. code-block:: yaml

    tasks:
      util :
        features : shlib
        source   :  { include : 'shlib/**/*.cpp' }
        includes : '.'
      program :
        features : program
        source   :  { include : 'prog/**/*.cpp' }
        includes : '.'
        use      : util

    buildtypes:
      debug :
        toolchain : auto-c++
      release :
        toolchain : g++
        cxxflags  : -O2
      default : debug

Once you have the config, run ``zenmake`` in the root of the project and
ZenMake does the build:

.. code-block:: console

    $ zenmake
    Configuring the project
    Setting top to                           : /tmp/testproject
    Setting out to                           : /tmp/testproject/build
    Checking for 'g++'                       : /usr/bin/g++
    Waf: Entering directory `/tmp/testproject/build/debug'
    [1/4] Compiling shlib/util.cpp
    [2/4] Compiling prog/test.cpp
    [3/4] Linking build/debug/libutil.so
    [4/4] Linking build/debug/program
    Waf: Leaving directory `/tmp/testproject/build/debug'
    'build' finished successfully (0.433s)

Running ZenMake without any parameters in a directory with ``buildconf.py`` or
``buildconf.yaml`` is the same as running ``zenmake build``. Otherwise it's
the same as ``zenmake help``.

Get the list of all commands with a short description using
``zenmake help`` or ``zenmake --help``. To get help on selected command you
can use ``zenmake help <selected command>`` or
``zenmake <selected comman> --help``

For example to build ``release`` of the project above such a command can
be used:

.. code-block:: console

    $ zenmake build -b release
    Setting top to                           : /tmp/testproject
    Setting out to                           : /tmp/testproject/build
    Checking for program 'g++, c++'          : /usr/bin/g++
    Checking for program 'ar'                : /usr/bin/ar
    Waf: Entering directory `/tmp/testproject/build/release'
    [1/4] Compiling shlib/util.cpp
    [2/4] Compiling prog/test.cpp
    [3/4] Linking build/release/libutil.so
    [4/4] Linking build/release/program
    Waf: Leaving directory `/tmp/testproject/build/release'
    'build' finished successfully (0.449s)

One of the effective and simple ways to learn something is to use
real examples.
Examples of projects can be found in the repository `here <repo_demo_projects_>`_.

