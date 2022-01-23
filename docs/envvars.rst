.. include:: global.rst.inc
.. highlight:: console
.. _envvars:

Environment variables
=====================

ZenMake supports some environment variables that can be used. Most of examples
are for POSIX platforms (Linux/MacOS) with ``gcc`` and ``clang`` installed.
Also see :ref:`bash-like substitutions<buildconf-substitutions-vars>`.

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
    For example it can be used to create deb/rpm/etc packages.
    Example::

        DESTDIR=dest zenmake install

.. _envvars-prefix:

PREFIX
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``prefix``
    as the installation prefix.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``. Example::

        PREFIX=/usr zenmake install

.. _envvars-execprefix:

EXEC_PREFIX
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``execprefix``
    as the installation prefix for machine-specific files.

.. _envvars-bindir:

BINDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``bindir``
    as the directory for installing executable programs that users can run.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.
    Example::

        BINDIR=/usr/bin zenmake install

.. _envvars-sbindir:

SBINDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``sbindir``
    as the directory for installing executable programs that can be run, but are
    only generally useful to system administrators.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-libexecdir:

LIBEXECDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``libexecdir``
    as the directory for installing executable programs to be run by other programs
    rather than by users.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-libdir:

LIBDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``libdir``
    as the installation directory for object files and libraries of object code.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-sysconfdir:

SYSCONFDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``sysconfdir``
    as the installation directory for read-only single-machine data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-sharedstatedir:

SHAREDSTATEDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``sharedstatedir``
    as the installation directory for modifiable architecture-independent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-localstatedir:

LOCALSTATEDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``localstatedir``
    as the installation directory for modifiable single-machine data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-includedir:

INCLUDEDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``includedir``
    as the installation directory for C header files.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-datarootdir:

DATAROOTDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``datarootdir``
    as the installation root directory for read-only architecture-independent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-datadir:

DATADIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``datadir``
    as the installation directory for read-only architecture-independent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-appdatadir:

APPDATADIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``appdatadir``
    as the installation directory for read-only architecture-independent application data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-docdir:

DOCDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``docdir``
    as the installation directory for documentation.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-mandir:

MANDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``mandir``
    as the installation directory for man documentation.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-infodir:

INFODIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``infodir``
    as the installation directory for info documentation.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-localedir:

LOCALEDIR
    Set value of :ref:`built-in<buildconf-builtin-vars>` variable ``localedir``
    as the installation directory for locale-dependent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

ZM_CACHE_CFGACTIONS
    When set to a 'True', 'true', 'yes' or non-zero number, ZenMake tries
    to use a cache for some :ref:`configuration actions<config-actions>`.
    Has no effect when ``--cache-cfg-actions`` is provided on the command line.
    It can speed up next runs of some configuration actions but also it can ignore
    changes in toolchains, system paths, etc. In general, it is safe to use it
    if there were no changes in the current system. Example::

        ZM_CACHE_CFGACTIONS=1 zenmake configure