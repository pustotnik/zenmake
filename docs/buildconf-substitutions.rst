.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-substitutions:

Build config: substitutions
===================================

.. _buildconf-substitutions-dynamic:

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

    You can not redefine internal variables.
