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
    task param you can use ``for`` and/or ``not-for`` in the same way as in
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
with ability to use system environment variables and built-in dynamic variables.

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

.. _buildconf-substitutions-builtin:

Built-in variables
"""""""""""""""""""""""

In some places (see descriptions of particular `task params<buildconf-taskparams>`)
you can use dynamic built-in substitutions to configure values. These variables are
resolved during the ``configure`` command. To avoid conflicts with environment and
bash-like variables the syntax is different a little bit:

in YAML format:

    .. code-block:: yaml

        param: '$(var)/some-string'

    in Python format:

    .. code-block:: python

        'param' : '$(var)/some-string'

List of built-in variables:

    :prjname:
        Name of the current project. See ``name`` :ref:`here<buildconf-project>`.

    :topdir:
        Absolute path of :ref:`startdir<buildconf-startdir>` of the top-level buildconf file.
        Usually it is root directory of the current project.

    :buildrootdir:
        Absolute path of :ref:`buildroot<buildconf-buildroot>`.

    :buildtypedir:
        Absolute path of current buildtype directory.

    :prefix:
        Installation prefix.

    :bindir:
        Installation bin directory.

    :libdir:
        Installation lib directory.

    :destdir:
        Installation destination directory. It's mostly for installing to a
        temporary directory. For example this can be used for building deb packages.
        See also ``--destdir`` command line argument for commands 'install'/'uninstall'.

In some cases some extra variables are provided. For example,
variables ``src`` and ``tgt`` are provided
for the ``cmd`` in the task parameter :ref:`run<buildconf-taskparams-run>`.

.. note::

    You cannot redefine built-in variables.
