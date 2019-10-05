.. include:: global.rst.inc
.. highlight:: console
.. _envvars:

Environment variables
=====================

ZenMake has some environment variables that can be used. Examples are for POSIX
platforms (Linux/MacOS) with ``gcc`` and ``clang`` installed. Some of these
variables just provided by Waf.

CC
    Set C compiler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        CC=clang zenmake build -v

CXX
    Set C++ compiler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        CXX=clang zenmake build -v

CFLAGS
    Set list of compilation flags for C files. It overrides values from
    :ref:`build config<buildconf>` if present. Example::

        CFLAGS='-O3 -fPIC' zenmake build -v

CXXFLAGS
    Set list of compilation flags for C++ files. It overrides values from
    :ref:`build config<buildconf>` if present. Example::

        CXXFLAGS='-O3 -fPIC' zenmake build -v

LDFLAGS
    Set list of link flags for C/C++ projects. It overrides values from
    :ref:`build config<buildconf>` if present. Example::

        LDFLAGS='-Wl,--as-needed' zenmake build -v

JOBS
    Default value for the amount of parallel jobs. Has no effect when -j is
    provided on the command line. Example::

        JOBS=2 zenmake build

NUMBER_OF_PROCESSORS
    Default value for the amount of parallel jobs when the JOBS environment
    variable is not provided; it is usually set on windows systems. Has no
    effect when -j is provided on the command line.

NOCOLOR
    When set to a non-empty value, colors in console outputs are disabled.
    Has no effect when --color is provided on the command line. Example::

        NOCOLOR=1 zenmake build

NOSYNC
    When set to a non-empty value, console outputs are displayed in an
    asynchronous manner; console text outputs may appear faster on some
    platforms. Example::

        NOSYNC=1 zenmake build
