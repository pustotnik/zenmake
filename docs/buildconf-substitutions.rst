.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-substitutions:

Build config: substitutions
===================================

In some places you can use substitution to configure values. It looks like
substitution in bash and uses following syntax:

    .. code-block:: python

        'param' : '${VAR}/some-string'

where ``VAR`` is a name of substitution. If you set this var to some value like this:

    .. code-block:: python

        substvars: {
            'VAR' : 'myvalue',
        }

then ``param`` from above example will be resolved as ``myvalue/some-string``.

Such variables can set in the
:ref:`root substvars<buildconf-substvars>` or in the
:ref:`task substvars<buildconf-taskparams-substvars>`. Root ``substvars`` are
visible in any build task while task ``substvars`` only in selected task.
If some name exist in the both ``substvars`` then value from task ``substvars``
will be used.

Also such variables can be set by some :ref:`config-actions<config-actions>`.
See ``var`` in config action ``find-program``.

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