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
    Set value of built-in variable :ref:`prefix<buildconf-builtin-vars-prefix>`
    as the installation prefix.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``. Example::

        PREFIX=/usr zenmake install

.. _envvars-execprefix:

EXEC_PREFIX
    Set value of built-in variable :ref:`execprefix<buildconf-builtin-vars-execprefix>`
    as the installation prefix for machine-specific files.

.. _envvars-bindir:

BINDIR
    Set value of built-in variable :ref:`bindir<buildconf-builtin-vars-bindir>`
    as the directory for installing executable programs that users can run.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.
    Example::

        BINDIR=/usr/bin zenmake install

.. _envvars-sbindir:

SBINDIR
    Set value of built-in variable :ref:`sbindir<buildconf-builtin-vars-sbindir>`
    as the directory for installing executable programs that can be run, but are
    only generally useful to system administrators.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-libexecdir:

LIBEXECDIR
    Set value of built-in variable :ref:`libexecdir<buildconf-builtin-vars-libexecdir>`
    as the directory for installing executable programs to be run by other programs
    rather than by users.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-libdir:

LIBDIR
    Set value of built-in variable :ref:`libdir<buildconf-builtin-vars-libdir>`
    as the installation directory for object files and libraries of object code.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-sysconfdir:

SYSCONFDIR
    Set value of built-in variable :ref:`sysconfdir<buildconf-builtin-vars-sysconfdir>`
    as the installation directory for read-only single-machine data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-sharedstatedir:

SHAREDSTATEDIR
    Set value of built-in variable :ref:`sharedstatedir<buildconf-builtin-vars-sharedstatedir>`
    as the installation directory for modifiable architecture-independent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-localstatedir:

LOCALSTATEDIR
    Set value of built-in variable :ref:`localstatedir<buildconf-builtin-vars-localstatedir>`
    as the installation directory for modifiable single-machine data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-includedir:

INCLUDEDIR
    Set value of built-in variable :ref:`includedir<buildconf-builtin-vars-includedir>`
    as the installation directory for C header files.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-datarootdir:

DATAROOTDIR
    Set value of built-in variable :ref:`datarootdir<buildconf-builtin-vars-datarootdir>`
    as the installation root directory for read-only architecture-independent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-datadir:

DATADIR
    Set value of built-in variable :ref:`datadir<buildconf-builtin-vars-datadir>`
    as the installation directory for read-only architecture-independent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-appdatadir:

APPDATADIR
    Set value of built-in variable :ref:`appdatadir<buildconf-builtin-vars-appdatadir>`
    as the installation directory for read-only architecture-independent application data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-docdir:

DOCDIR
    Set value of built-in variable :ref:`docdir<buildconf-builtin-vars-docdir>`
    as the installation directory for documentation.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-mandir:

MANDIR
    Set value of built-in variable :ref:`mandir<buildconf-builtin-vars-mandir>`
    as the installation directory for man documentation.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-infodir:

INFODIR
    Set value of built-in variable :ref:`infodir<buildconf-builtin-vars-infodir>`
    as the installation directory for info documentation.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-localedir:

LOCALEDIR
    Set value of built-in variable :ref:`localedir<buildconf-builtin-vars-localedir>`
    as the installation directory for locale-dependent data.
    This path is always considered as an absolute path or
    as a relative path to ``DESTDIR``.

.. _envvars-qt5bindir:

QT5_BINDIR
    Set the bin directory of the installed Qt5 toolkit. This directory must
    contain such tools like qmake, moc, uic, etc.
    This path must be absolute native path or path relative
    to the current working directory but last variant is not recommended.
    This variable can be especially useful for standalone installation of Qt5,
    for example on Windows.
    The ``PATH`` and ``QT5_SEARCH_ROOT`` environment variables are ignored
    if ``QT5_BINDIR`` is not empty.

.. _envvars-qt5libdir:

QT5_LIBDIR
    Set the library directory of the installed Qt5 toolkit.
    This path must be absolute native path or path relative
    to the current working directory but last variant is not recommended.
    Usually you don't need to use this variable if you
    set the ``QT5_BINDIR`` variable.

.. _envvars-qt5includes:

QT5_INCLUDES
    Set the directory with 'includes' of the installed Qt5 toolkit.
    This path must be absolute native path or path relative
    to the current working directory but last variant is not recommended.
    Usually you don't need to use this variable if you
    set the ``QT5_BINDIR`` variable. This variable has no effect
    on systems with pkg-config/pkgconf installed (while you
    don't turn on the :ref:`QT5_NO_PKGCONF<envvars-qt5nopkgconf>`).

.. _envvars-qt5searchroot:

QT5_SEARCH_ROOT
    Set the root directory to search for installed Qt5 toolkit(s).
    ZenMake will try to find the bin directories of all Qt5 toolkits in this
    directory recursively. Dot not set this variable to path like ``/`` or ``C:\``
    because it will slow down the detection very much.
    Qt5 toolkits found in this directory have priority over values from
    the ``PATH`` environment variable.
    You can set more than one directories using path separator
    (``;`` on Windows and ``:`` on other OS) like this::

        QT5_SEARCH_ROOT=/usr/local/qt:/usr/local/opt/qt zenmake

    It defaults to ``C:\Qt`` on Windows.
    Usually you don't need to use this variable on Linux.

.. _envvars-qt5minver:

QT5_MIN_VER
    Set minimum version of Qt5. For example it can be  ``5.1`` or ``5.1.2``.

.. _envvars-qt5maxver:

QT5_MAX_VER
    Set maximum version of Qt5. For example it can be  ``5.12`` or ``5.12.2``.

.. _envvars-qt5usehighestver:

QT5_USE_HIGHEST_VER
    By default ZenMake will use first useful version of Qt5.
    When this variable set to a 'True', 'true', 'yes' or non-zero number then
    ZenMake will try to use the highest version of Qt5 among found versions.

.. _envvars-qt5nopkgconf:

QT5_NO_PKGCONF
    When set to a 'True', 'true', 'yes' or non-zero number,
    ZenMake will not use pkg-config/pkgconf
    to configure building with Qt5.
    Usually you don't need to use this variable.

.. _envvars-qt5tools:

QT5_{MOC,UIC,RCC,LRELEASE,LUPDATE}
    These variables can be used to specify full file paths to Qt5 tools
    ``moc``, ``uic``, ``rcc``, ``lrelease`` and ``lupdate``.
    Usually you don't need to use these variables.

ZM_CACHE_CFGACTIONS
    When set to a 'True', 'true', 'yes' or non-zero number, ZenMake tries
    to use a cache for some :ref:`configuration actions<config-actions>`.
    Has no effect when ``--cache-cfg-actions`` is provided on the command line.
    It can speed up next runs of some configuration actions but also it can ignore
    changes in toolchains, system paths, etc. In general, it is safe to use it
    if there were no changes in the current system. Example::

        ZM_CACHE_CFGACTIONS=1 zenmake configure