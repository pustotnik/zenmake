.. include:: global.rst.inc
.. highlight:: console
.. _envvars:

Environment variables
=====================

ZenMake supports some environment variables that can be used. Most of examples
are for POSIX platforms (Linux/MacOS) with ``gcc`` and ``clang`` installed.
Some of these variables just provided by Waf.

AR
    Set archive-maintaining program.

CC
    Set C compiler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        CC=clang zenmake build -B

CXX
    Set C++ compiler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        CXX=clang++ zenmake build -B

DC
    Set D compiler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        DC=ldc2 zenmake build -B

FC
    Set Fortran compiler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        FC=gfortran zenmake build -B

AS
    Set Assembler. It can be name of installed a system compiler or any path
    to existing compiler. It overrides values from :ref:`build config<buildconf>`
    if present. Example::

        AS=gcc zenmake build -B

ARFLAGS
    Flags to give the archive-maintaining program.

CFLAGS
    Extra flags to give to the C compiler. Example::

        CFLAGS='-O3 -fPIC' zenmake build -B

CXXFLAGS
    Extra flags to give to the C++ compiler. Example::

        CXXFLAGS='-O3 -fPIC' zenmake build -B

CPPFLAGS
    Extra flags added at the end of compilation commands for C/C++.

DFLAGS
    Extra flags to give to the D compiler. Example::

        DFLAGS='-O' zenmake build -B
FCFLAGS
    Extra flags to give to the Fortran compiler. Example::

        FCFLAGS='-O0' zenmake build -B

ASFLAGS
    Extra flags to give to the Assembler. Example::

        ASFLAGS='-Os' zenmake build -B

LINKFLAGS
    Extra list of linker flags for C/C++/D/Fortran. Example::

        LINKFLAGS='-Wl,--as-needed' zenmake build -B

LDFLAGS
    Extra list of linker flags at the end of the link command for C/C++/D/Fortran. Example::

        LDFLAGS='-Wl,--as-needed' zenmake build -B

ASLINKFLAGS
    Extra list of linker flags for Assembler files. Example::

        ASLINKFLAGS='-s' zenmake build -B

JOBS
    Default value for the amount of parallel jobs. Has no effect when ``-j`` is
    provided on the command line. Example::

        JOBS=2 zenmake build

NUMBER_OF_PROCESSORS
    Default value for the amount of parallel jobs when the JOBS environment
    variable is not provided; it is usually set on windows systems. Has no
    effect when ``-j`` is provided on the command line.

NOCOLOR
    When set to a non-empty value, colors in console outputs are disabled.
    Has no effect when ``--color`` is provided on the command line. Example::

        NOCOLOR=1 zenmake build

NOSYNC
    When set to a non-empty value, console outputs are displayed in an
    asynchronous manner; console text outputs may appear faster on some
    platforms. Example::

        NOSYNC=1 zenmake build

BUILDROOT
    A path to the root of a project build directory.
    The path can be absolute or relative to the current directory.
    See also :ref:`buildroot<buildconf-buildroot>`.
    Example::

        BUILDROOT=bld zenmake build

DESTDIR
    Default installation base directory when ``--destdir`` is not provided on
    the command line. It's mostly for installing to a temporary directory.
    For example this is used when building deb packages.
    Example::

        DESTDIR=dest zenmake install

PREFIX
    Default installation prefix when ``--prefix`` is not provided on the
    command line. Example::

        PREFIX=/usr/local/ zenmake install

BINDIR
    Default installation bin directory when ``--bindir`` is not provided on the
    command line. It ignores value of ``PREFIX`` if set. Example::

        BINDIR=/usr/local/bin zenmake install

LIBDIR
    Default installation lib directory when ``--libdir`` is not provided on the
    command line. It ignores value of ``PREFIX`` if set. Example::

        LIBDIR=/usr/local/lib64 zenmake install

ZM_CACHE_CFGACTIONS
    When set to a 'True', 'true', 'yes' or non-zero number, ZenMake tries
    to use a cache for some :ref:`configuration actions<config-actions>`.
    Has no effect when ``--cache-cfg-actions`` is provided on the command line.
    It can speed up next runs of some configuration actions but also it can ignore
    changes in toolchains, system paths, etc. In general, it is safe to use it
    if there were no changes in the current system. Example::

        ZM_CACHE_CFGACTIONS=1 zenmake configure