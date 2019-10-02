.. include:: global.rst.inc
.. _quickstart:

Quickstart guide
================

To use ZenMake you need :ref:`ZenMake<installation>` and
:ref:`buildconf<buildconf>` file in the root of your project.

Let's consider an example with such a structure::

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
            'features' : 'cxxshlib',
            'source'   :  { 'include' : 'shlib/**/*.cpp' },
            'includes' : '.',
        },
        'program' : {
            'features' : 'cxxprogram',
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
       Resulting target names will be made depending on platform. For example,
       on Windows 'program' will result to 'program.exe'.
3      Mark build task as C++ shared library.
4      Specify all \*.cpp files in the directory 'shlib' recursively.
5,10   Specify path for C/C++ headers relative to project root directory.
       Actually here it's not necessary because ZenMake add project root
       directory itself. But it's an example.
8      Mark build task as C++ executable.
9      Specify all \*.cpp files in the directory 'prog' recursively.
11     Specify task 'util' as dependency to task 'program'.
15     Section with build types.
16,19  Names of build types. They can be almost any.
17     Specify auto detecting system C++ compiler.
20     Specify g++ compiler (from gcc).
21     Specify C++ compiler flags.
23     Special case: specify default build type that is used when no build
       type was specifying for ZenMake command.
=====  =======================================================================

In case of using YAML the file ``buildconf.yaml`` with the same values for this
case can be like that:

.. code-block:: yaml

    tasks:
      util :
        features : cxxshlib
        source   :  { include : 'shlib/**/*.cpp' }
        includes : '.'
      program :
        features : cxxprogram
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

Then you can run ``zenmake`` in the root of project and ZenMake will build
current project:

.. code-block:: console

    $ zenmake
    Configuring the project
    Setting top to                           : /tmp/testproject
    Setting out to                           : /tmp/testproject/build/out
    Checking for 'g++'                       : /usr/bin/g++
    Waf: Entering directory `/tmp/testproject/build/out/debug'
    [1/4] Compiling shlib/util.cpp
    [2/4] Compiling prog/test.cpp
    [3/4] Linking build/out/debug/libutil.so
    [4/4] Linking build/out/debug/program
    Waf: Leaving directory `/tmp/testproject/build/out/debug'
    'build' finished successfully (0.433s)

Running ZenMake without any parameters in a directory with ``buildconf.py`` or
``buildconf.yaml`` is equal to run ``zenmake build``. Otherwise it's equal to
``zenmake help``.

List of all commands with a short description can be gotten with
``zenmake help`` or ``zenmake --help``. To get help on selected command you
can use ``zenmake help <selected command>`` or
``zenmake <selected comman> --help``

For example to build ``release`` of the project above such a command can
be used:

.. code-block:: console

    $ zenmake build -b release
    Setting top to                           : /tmp/testproject
    Setting out to                           : /tmp/testproject/build/out
    Checking for program 'g++, c++'          : /usr/bin/g++
    Checking for program 'ar'                : /usr/bin/ar
    Waf: Entering directory `/tmp/testproject/build/out/release'
    [1/4] Compiling shlib/util.cpp
    [2/4] Compiling prog/test.cpp
    [3/4] Linking build/out/release/libutil.so
    [4/4] Linking build/out/release/program
    Waf: Leaving directory `/tmp/testproject/build/out/release'
    'build' finished successfully (0.449s)

More examples of projects can be found in repository `here <repo_test_projects_>`_.

