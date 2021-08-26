.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-substitutions:

Build config: substitutions
===================================

There are two types of substitutions in ZenMake: static and dynamic substitutions.

.. _buildconf-substitutions-dynamic:

Dynamic substitutions
------------------------

In some places you can use dynamic substitutions to configure values. It looks like
substitutions in bash and uses following syntax:

    in YAML format:

    .. code-block:: yaml

        param: '${VAR}/some-string'

    in Python format:

    .. code-block:: python

        'param' : '${VAR}/some-string'

where ``VAR`` is a name of substitution. If you set this var to some value like this:

    in YAML format:

    .. code-block:: yaml

        substvars:
            VAR: 'myvalue'

    in Python format:

    .. code-block:: python

        substvars: {
            'VAR' : 'myvalue',
        }

then ``param`` from above example will be resolved as ``myvalue/some-string``.

.. note::

    See a particular parameter in documentaion to check out if it supports
    substitutions.

Such substitution variables can be set in the
:ref:`root substvars<buildconf-substvars>` or in the
:ref:`task substvars<buildconf-taskparams-substvars>`. Values from root
``substvars`` are visible in any build task while values from task ``substvars``
are visible only in selected task (but they can be :ref:`exported<buildconf-taskparams-export>`).
If some name exists in the both ``substvars`` then value from task ``substvars``
will be used.

Also such variables can be set by some :ref:`configuration actions<config-actions>`.
For example see ``var`` in configuration action ``find-program``.

There are some variables which ZenMake sets always:

    :PROJECT_NAME:
        Name of the current project. See ``name`` :ref:`here<buildconf-project>`.

    :TOP_DIR:
        Absolute path of :ref:`startdir<buildconf-startdir>` of the top-level buildconf file.
        Usually it is root directory of the current project.

    :BUILDROOT_DIR:
        Absolute path of :ref:`buildroot<buildconf-buildroot>`.

    :BUILDTYPE_DIR:
        Absolute path of current buildtype directory.

    :PREFIX:
        Installation prefix.

    :BINDIR:
        Installation bin directory.

    :LIBDIR:
        Installation lib directory.

    :DESTDIR:
        Installation destination directory. It's mostly for installing to a
        temporary directory. For example this is used when building deb packages.
        See also ``--destdir`` command line argument for commands 'install'/'uninstall'.

In some cases some extra variables are provided. For example,
variables ``SRC`` and ``TGT`` are provided
for the ``cmd`` in the task parameter :ref:`run<buildconf-taskparams-run>`.

.. note::

    You cannot redefine internal variables.

.. _buildconf-substitutions-static:

Static substitutions
------------------------

Dynamic substitutions can be used both in YAML and python formats
but this type can be used only in some places, not everywhere. In python format
the full power of the python language can be used to make any kind of substitution
but YAML format has some constraints and does not support substitutions in specification.
In some cases you can use YAML anchors and aliases but this method is a
little verbose, not very obvious and cannot be used as a substitution inside a string.

ZenMake supports static substitution variables that has syntax similar to syntax
of dynamic substitutions but are proccessed during parsing of YAML buildconf data
and before actual running of any command like ``configure`` or ``build``.

.. note::

    This type of substitutions can be used only in YAML format.

Static substitutions use following syntax:

.. code-block:: yaml

    param: some-string/$VAR/some-string

or

.. code-block:: yaml

    param: some-string/${{VAR}}/some-string

where ``VAR`` is a name of substitution.

The second form is needed mostly when a substitution is used inside some word like this:

.. code-block:: yaml

    param: env${{VAR}}ment

Values for static substitution variables can be set in environment variables or/and
in special section of YAML buildconf that is named as YAML document
with ``---`` separator. For example:

.. code-block:: yaml

    # Here is section with values for static substitution variables

    # set 'fragment' variable
    fragment: |
      program
      end program

    # set 'GCC_BASE_FLAGS' variable
    GCC_BASE_FLAGS: -std=f2018 -Wall

    --- # <-- DOCUMENT SEPARATOR

    # Here is normal buildconf data

    tasks:

    # ... skipped values

      test:
        features : fcprogram
        source   : src/calculator.f90 src/main.f90
        includes : src/inc
        use      : staticlib sharedlib
        configure:
          - do: check-code
            text: $fragment # <-- substitution
            label: fragment

    buildtypes:
      debug  : { fcflags: $GCC_BASE_FLAGS -O0 }
      release: { fcflags: $GCC_BASE_FLAGS -O2 }
      default: debug

.. note::

    This YAML document with values for static substitution variables
    inside buildconf file must be either before YAML document with the regular
    buildconf data or not used at all.

There are some constraints due to YAML specification and such substitutions
cannot be used inside quoted string as is:

.. code-block:: yaml

    debug  : { fcflags: $GCC_BASE_FLAGS -O0 }   # works
    debug  : { fcflags: "$GCC_BASE_FLAGS -O0" } # doesn't work
    debug  : { fcflags: '$GCC_BASE_FLAGS -O0' } # doesn't work

But there are several ways to solve this problem in ZenMake YAML buildconf file:

    - Not use quoted text if possible. In YAML such strings are called as
      plain scalars: https://www.yaml.info/learn/quote.html

    - Use YAML tag ``!subst`` before a quoted string:

      .. code-block:: yaml

        debug  : { fcflags: !subst "$GCC_BASE_FLAGS -O0" } # works
        debug  : { fcflags: !subst '$GCC_BASE_FLAGS -O0' } # works

    - Use special variable ``substmode`` with 'preparse' or 'preparse-noenv' value
      to set alternative mode of processing static substitution variables.
      In this mode all such variables are proccessed in whole YAML text before
      actual parsing of YAML data. But this mode is not recommended in general
      because it ignores all YAML syntax what can cause
      some unexpected substitutions.

      .. code-block:: yaml

        substmode: preparse # must be in first YAML document

        GCC_BASE_FLAGS: -std=f2018 -Wall

        ---

        # skipped all other structures and values

        debug1 : { fcflags: "$GCC_BASE_FLAGS -O0" } # works
        debug2 : { fcflags: '$GCC_BASE_FLAGS -O0' } # works

Zenmake supports following values for ``substmode`` variable:

    :yaml-tag:
        This is default mode in which YAML format is used as usually but with
        ability to use substitutions. System environment variables always replace
        corresponded values of substitution variables from first YAML document
        in the buildconf file. In this mode substitution variables inside
        buildconf file can be considered as default values for environment
        variables.
    :yaml-tag-noenv:
        The same as ``yaml-tag`` mode but in this mode environment variables are not used at all.
        Only substitution variables inside buildconf file are used.
    :preparse:
        In this mode all substitution variables are proccessed in whole YAML
        text before actual parsing of YAML data with  regexp.
        This mode is not recommended in general because it ignores all
        YAML syntax.
        As for ``yaml-tag`` system environment variables are used here.
    :preparse-noenv:
        The same as ``preparse`` mode but in this mode environment variables are not used at all.
        Only substitution variables inside buildconf file are used.
