.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-extended-syntax:

Build config: extended syntax
===================================

For convenience, ZenMake supports some syntax extensions in buildconf files.

.. _buildconf-syntactic-sugar:

Syntactic sugar
-----------------------------------

There are some syntactic sugar constructions that can be used to make a buildconf
a little shorter.

configure
""""""""""

    It can be used as a replacement for :ref:`configure<buildconf-taskparams-configure>` task param.

    For example you have (in YAML format):

    .. code-block:: yaml

        tasks:
          util:
            features : cshlib
            source   : shlib/**/*.c
            configure:
              - do: check-headers
                names : stdio.h

          test:
            features : cprogram
            source   : prog/**/*.c
            use      : util
            configure:
              - do: check-headers
                names : stdio.h

    So it can be converting into this:

    .. code-block:: yaml

        tasks:
          util:
            features : cshlib
            source   : shlib/**/*.c

          test:
            features : cprogram
            source   : prog/**/*.c
            use      : util

        configure:
          - do: check-headers
            names : stdio.h

    The ``configure`` above is the same as following construction:

    .. code-block:: yaml

        byfilter:
          - for: all
            set:
              configure:
                - do: check-headers
                  names : stdio.h

    In addition to regular arguments for :ref:`configure<buildconf-taskparams-configure>`
    task param you can use ``for``/``not-for``/``if`` in the same way as in
    the :ref:`byfilter<buildconf-byfilter>`.

    Example:

    .. code-block:: yaml

        tasks:
          # .. skipped

        configure:
          - do: check-headers
            names : stdio.h
            not-for: { task: mytask }

install
""""""""""

    Like as previous ``configure`` this can be used as a replacement for
    :ref:`install-files<buildconf-taskparams-install-files>` task param.

    Example:

    .. code-block:: yaml

        tasks:
          # .. skipped

        install:
          - for: { task: gui }
            src: 'some/src/path/ui.res'
            dst: '$(prefix)/share/$(prjname)'

.. _buildconf-substitutions:

Substitutions
-----------------------------------

There are two types of substitutions in ZenMake: bash-like variables
with ability to use system environment variables and built-in variables.

.. _buildconf-substitutions-vars:

Bash-like variables
"""""""""""""""""""""""

ZenMake supports substitution variables with syntax similar to syntax
of bash variables.

Both $VAR and ${VAR} syntax are supported. These variables can be used in any
buildconf parameter value of string/text type.

    in YAML format:

    .. code-block:: yaml

        param: '${VAR}/some-string'

    in Python format:

    .. code-block:: python

        'param' : '${VAR}/some-string'

ZenMake looks such variables in environment variables at first and
then in the buildconf file. You can use a $$ (double-dollar sign) to prevent
use of environment variables.

Example in YAML format:

.. code-block:: yaml

    # set 'fragment' variable
    fragment: |
      program
      end program

    # set 'GCC_BASE_FLAGS' variable
    GCC_BASE_FLAGS: -std=f2018 -Wall

    tasks:

    # ... skipped values

      test:
        features : fcprogram
        source   : src/calculator.f90 src/main.f90
        includes : src/inc
        use      : staticlib sharedlib
        configure:
          - do: check-code
            text: $$fragment # <-- substitution without env
            label: fragment

    buildtypes:
      # GCC_BASE_FLAGS can be overwritten by environment variable with the same name
      debug  : { fcflags: $GCC_BASE_FLAGS -O0 }
      release: { fcflags: $GCC_BASE_FLAGS -O2 }
      default: debug

.. note::

    These substitution variables inherit values from parent buildconf in
    :ref:`subdirs<dependencies-subdirs>`.

Also values for such variables can be set by some :ref:`configuration actions<config-actions>`.
For example see ``var`` in configuration action ``find-program``. But in this case
these values are not visible everywhere.

For YAML format there are some constraints with ${VAR} form due to YAML specification:

.. code-block:: yaml

    debug  : { fcflags: $GCC_BASE_FLAGS -O0 }     # works
    debug  : { fcflags: "$GCC_BASE_FLAGS -O0" }   # works
    debug  : { fcflags: ${GCC_BASE_FLAGS} -O0 }   # doesn't work
    debug  : { fcflags: "${GCC_BASE_FLAGS} -O0" } # works
    debug  :
      fcflags: ${GCC_BASE_FLAGS} -O0              # works

.. _buildconf-builtin-vars:

Built-in variables
"""""""""""""""""""""""

ZenMake has some built-in variables that can be used as substitutions.
To avoid possible conflicts with environment and bash-like variables the syntax of
substitutions is a little bit different in this case:

in YAML format:

    .. code-block:: yaml

        param: '$(var)/some-string'

    in Python format:

    .. code-block:: python

        'param' : '$(var)/some-string'

List of built-in variables:

.. _buildconf-builtin-vars-prjname:

    prjname
        Name of the current project.
        It can be changed via ``name`` from :ref:`here<buildconf-project>`.

.. _buildconf-builtin-vars-topdir:

    topdir
        Absolute path of :ref:`startdir<buildconf-startdir>` of the top-level buildconf file.
        Usually it is root directory of the current project.

.. _buildconf-builtin-vars-buildrootdir:

    buildrootdir
        Absolute path of :ref:`buildroot<buildconf-buildroot>`.

.. _buildconf-builtin-vars-buildtypedir:

    buildtypedir
        Absolute path of current buildtype directory. It is
        current value of :ref:`buildroot<buildconf-buildroot>` plus current buildtype.

.. _buildconf-builtin-vars-prefix:

    prefix
        The installation prefix. It is a directory that is prepended onto all
        install directories and it defaults to ``/usr/local`` on UNIX and
        ``C:/Program Files/$(prjname)`` on Windows.
        It can be changed via environment variable :ref:`PREFIX<envvars-prefix>`
        or via ``--prefix`` on the command line.

.. _buildconf-builtin-vars-execprefix:

    execprefix
        The installation prefix for machine-specific files. In most cases it is
        the same as the ``$(prefix)`` variable.
        It was introduced mostly for compatibility with GNU standard:
        https://www.gnu.org/prep/standards/html_node/Directory-Variables.html.
        It can be changed via environment variable :ref:`EXEC_PREFIX<envvars-execprefix>`
        or via ``--execprefix`` on the command line.

.. _buildconf-builtin-vars-bindir:

    bindir
        The directory for installing executable programs that users can run.
        It defaults to ``$(exeprefix)/bin`` on UNIX and ``$(exeprefix)`` on Windows.
        It can be changed via environment variable :ref:`BINDIR<envvars-bindir>`
        or via ``--bindir`` on the command line.

.. _buildconf-builtin-vars-sbindir:

    sbindir
        The directory for installing executable programs that can be run, but
        are only generally useful to system administrators.
        It defaults to ``$(exeprefix)/sbin`` on UNIX and ``$(exeprefix)`` on Windows.
        It can be changed via environment variable :ref:`SBINDIR<envvars-sbindir>`
        or via ``--sbindir`` on the command line.

.. _buildconf-builtin-vars-libexecdir:

    libexecdir
        The directory for installing executable programs to be run by other
        programs rather than by users.
        It defaults to ``$(exeprefix)/libexec`` on UNIX and ``$(exeprefix)`` on Windows.
        It can be changed via environment variable :ref:`LIBEXECDIR<envvars-libexecdir>`
        or via ``--libexecdir`` on the command line.

.. _buildconf-builtin-vars-libdir:

    libdir
        The installation directory for object files and libraries of object code.
        It defaults to ``$(exeprefix)/lib`` or ``$(exeprefix)/lib64`` on UNIX
        and ``$(exeprefix)`` on Windows.
        It can be changed via environment variable :ref:`LIBDIR<envvars-libdir>`
        or via ``--libdir`` on the command line.

.. _buildconf-builtin-vars-sysconfdir:

    sysconfdir
        The installation directory for read-only single-machine data.
        It defaults to ``$(prefix)/etc`` on UNIX and ``$(prefix)`` on Windows.
        It can be changed via environment variable :ref:`SYSCONFDIR<envvars-sysconfdir>`
        or via ``--sysconfdir`` on the command line.

.. _buildconf-builtin-vars-sharedstatedir:

    sharedstatedir
        The installation directory for modifiable architecture-independent data.
        It defaults to ``/var/lib`` on UNIX and ``$(prefix)`` on Windows.
        It can be changed via environment variable :ref:`SHAREDSTATEDIR<envvars-sharedstatedir>`
        or via ``--sharedstatedir`` on the command line.

.. _buildconf-builtin-vars-localstatedir:

    localstatedir
        The installation directory for modifiable single-machine data.
        It defaults to ``$(prefix)/var``.
        It can be changed via environment variable :ref:`LOCALSTATEDIR<envvars-localstatedir>`
        or via ``--localstatedir`` on the command line.

.. _buildconf-builtin-vars-includedir:

    includedir
        The installation directory for C header files.
        It defaults to ``$(prefix)/include``.
        It can be changed via environment variable :ref:`INCLUDEDIR<envvars-includedir>`
        or via ``--includedir`` on the command line.

.. _buildconf-builtin-vars-datarootdir:

    datarootdir
        The installation root directory for read-only architecture-independent data.
        It defaults to ``$(prefix)/share`` on UNIX and ``$(prefix)`` on Windows.
        It can be changed via environment variable :ref:`DATAROOTDIR<envvars-datarootdir>`
        or via ``--datarootdir`` on the command line.

.. _buildconf-builtin-vars-datadir:

    datadir
        The installation directory for read-only architecture-independent data.
        It defaults to ``$(datarootdir)``.
        It can be changed via environment variable :ref:`DATADIR<envvars-datadir>`
        or via ``--datadir`` on the command line.

.. _buildconf-builtin-vars-appdatadir:

    appdatadir
        The installation directory for read-only architecture-independent application data.
        It defaults to ``$(datarootdir)/$(prjname)`` on UNIX
        and ``$(datarootdir)`` on Windows.
        It can be changed via environment variable :ref:`APPDATADIR<envvars-appdatadir>`
        or via ``--appdatadir`` on the command line.

.. _buildconf-builtin-vars-docdir:

    docdir
        The installation directory for documentation.
        It defaults to ``$(datarootdir)/doc/$(prjname)`` on UNIX
        and ``$(datarootdir)/doc`` on Windows.
        It can be changed via environment variable :ref:`DOCDIR<envvars-docdir>`
        or via ``--docdir`` on the command line.

.. _buildconf-builtin-vars-mandir:

    mandir
        The installation directory for man documentation.
        It defaults to ``$(datarootdir)/man``.
        It can be changed via environment variable :ref:`MANDIR<envvars-mandir>`
        or via ``--mandir`` on the command line.

.. _buildconf-builtin-vars-infodir:

    infodir
        The installation directory for info documentation.
        It defaults to ``$(datarootdir)/info``.
        It can be changed via environment variable :ref:`INFODIR<envvars-infodir>`
        or via ``--infodir`` on the command line.

.. _buildconf-builtin-vars-localedir:

    localedir
        The installation directory for locale-dependent data.
        It defaults to ``$(datarootdir)/locale``.
        It can be changed via environment variable :ref:`LOCALEDIR<envvars-localedir>`
        or via ``--localedir`` on the command line.

In some cases some extra variables are provided. For example,
variables ``src`` and ``tgt`` are provided
for the ``cmd`` in the task parameter :ref:`run<buildconf-taskparams-run>`.

Built-in variables cannot be used in buildconf parameters which are used to
determine values of that built-in variables. These parameters are:

  - :ref:`startdir<buildconf-startdir>`, :ref:`buildroot<buildconf-buildroot>`,
    :ref:`realbuildroot<buildconf-realbuildroot>`
  - **buildtypedir** only: the ``default`` in the :ref:`buildtypes<buildconf-buildtypes>`
  - **buildtypedir** only: the ``buildtypes``, ``platform`` and  ``task`` in
    the :ref:`byfilter<buildconf-byfilter>`
