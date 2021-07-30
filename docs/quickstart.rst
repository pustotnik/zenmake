.. include:: global.rst.inc
.. highlight:: bash
.. _quickstart:

Quickstart guide
================

To use ZenMake you need :ref:`ZenMake<installation>` and
:ref:`buildconf<buildconf>` file in the root of your project.

Let's consider an example with this structure::

    testproject
    ├── buildconf.yaml
    ├── prog
    │   └── test.cpp
    └── shlib
        ├── util.cpp
        └── util.h

For this project ``buildconf.yaml`` can be like that:

.. code-block:: yaml
    :linenos:

    tasks:
      util :
        features : cxxshlib
        source   : 'shlib/**/*.cpp'
        includes : '.'
      program :
        features : cxxprogram
        source   : 'prog/**/*.cpp'
        includes : '.'
        use      : util

    buildtypes:
      debug :
        toolchain : clang++
        cxxflags  : -O0 -g
      release :
        toolchain : g++
        cxxflags  : -O2
      default : debug

=====  =======================================================================
Lines  Description
=====  =======================================================================
1      Section with build tasks
2,6    Names of build tasks. By default they are used as target names.
       Resulting target names will be adjusted depending on a platform.
       For example, on Windows 'program' will result to 'program.exe'.
3      Mark build task as a C++ shared library.
4      Specify all \*.cpp files in the directory 'shlib' recursively.
5,9    Specify the path for C/C++ headers relative to the project root directory.
       In this example, this parameter is optional as ZenMake adds the
       project root directory itself. But it's an example.
7      Mark build task as a C++ executable.
8      Specify all \*.cpp files in the directory 'prog' recursively.
10     Specify task 'util' as dependency to task 'program'.
12     Section with build types.
13,16  Names of build types. They can be almost any.
14     Specify Clang C++ compiler for debug.
15     Specify C++ compiler flags for debug.
17     Specify g++ compiler (from GCC) for release.
18     Specify C++ compiler flags for release.
19     Special case: specify default build type that is used when no build
       type was specified for ZenMake command.
=====  =======================================================================

In case of using python config the file ``buildconf.py`` with the same values as above
would look like this:

.. code-block:: python

    tasks = {
        'util' : {
            'features' : 'cxxshlib',
            'source'   : 'shlib/**/*.cpp',
            'includes' : '.',
        },
        'program' : {
            'features' : 'cxxprogram',
            'source'   : 'prog/**/*.cpp',
            'includes' : '.',
            'use'      : 'util',
        },
    }

    buildtypes = {
        'debug' : {
            'toolchain' : 'clang++',
            'cxxflags'  : '-O0 -g',
        },
        'release' : {
            'toolchain' : 'g++',
            'cxxflags'  : '-O2',
        },
        'default' : 'debug',
    }


Once you have the config, run ``zenmake`` in the root of the project and
ZenMake does the build:

.. code-block:: console

    $ zenmake
    * Project name: 'testproject'
    * Build type: 'debug'
    Setting top to                           : /tmp/testproject
    Setting out to                           : /tmp/testproject/build
    Checking for 'clang++'                   : /usr/lib/llvm/11/bin/clang++
    [1/4] Compiling shlib/util.cpp
    [2/4] Compiling prog/test.cpp
    [3/4] Linking build/debug/libutil.so
    [4/4] Linking build/debug/program
    'build' finished successfully (0.531s)

Running ZenMake without any parameters in a directory with ``buildconf.py`` or
``buildconf.yaml`` is the same as running ``zenmake build``. Otherwise it's
the same as ``zenmake help``.

Get the list of all commands with a short description using
``zenmake help`` or ``zenmake --help``. To get help on selected command you
can use ``zenmake help <selected command>`` or
``zenmake <selected command> --help``

For example to build ``release`` of the project above such a command can
be used:

.. code-block:: console

    $ zenmake build -b release
    * Project name: 'testproject'
    * Build type: 'release'
    Setting top to                           : /tmp/testproject
    Setting out to                           : /tmp/testproject/build
    Checking for 'g++'                       : /usr/bin/g++
    [1/4] Compiling shlib/util.cpp
    [2/4] Compiling prog/test.cpp
    [3/4] Linking build/release/libutil.so
    [4/4] Linking build/release/program
    'build' finished successfully (0.498s)

One of the effective and simple ways to learn something is to use
real examples.
Examples of projects can be found in the repository `here <repo_demo_projects_>`_.

