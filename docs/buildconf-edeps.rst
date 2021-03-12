.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-edep-params:

Build config: edeps
=============================

The config parameter ``edeps`` is a :ref:`dict<buildconf-dict-def>` with
configurations of external non-system dependencies.
General description of external dependencies is :ref:`here<dependencies-external>`.

Each such a dependency can have own unique name and parameters:

.. _buildconf-edep-params-rootdir:

rootdir
"""""""""""""""""""""
    A path to the root of the dependency project. It should be path to directory
    with the build script of the dependency project.
    This path can be relative to the :ref:`startdir<buildconf-startdir>` or absolute.

targets
"""""""""""""""""""""
    A :ref:`dict<buildconf-dict-def>` with descriptions of targets of the
    dependency project. Each target has a reference name which can be in
    :ref:`use<buildconf-taskparams-use>` in format
    ``dependency-name:target-reference-name`` and parameters:

    :dir:
        A path with the current target file. Usually it's some build directory.
        This path can be relative to the :ref:`startdir<buildconf-startdir>` or absolute.

    :type:
        It's type of the target file. This type has effects to the link of
        the build tasks and some other things. Supported types:

        :stlib:
            The target file is a static library.

        :shlib:
            The target file is a shared library.

        :program:
            The target file is an executable file.

        :file:
            The target file is any file.

    :name:
        It is a base name of the target file which is used
        for detecting of resulting target file name depending on destination
        operation system, selected toolchain, value of ``type``, etc.

        If it's not set the target reference name is used.

    :ver-num:
        It's a version number for the target file if it is a shared library.
        It can have effect on resulting target file name.

    :fname:
        It's a real file name of the target. Usually it's detected by ZenMake
        from other parameters but you can set it manually but it's not
        recommended until you really need it.
        If parameter ``type`` is equal to ``file`` the value of this parameter
        is always equal to value of parameter ``name`` by default.

    Example in Python format for non-ZenMake dependency:

    .. code-block:: python

        'targets': {
            # 'shared-lib' and 'static-lib' are target reference names
            'shared-lib' : {
                'dir' : '../foo-lib/_build_/debug',
                'type': 'shlib',
                'name': 'fooutil',
            },
            'static-lib' : {
                'dir' : '../foo-lib/_build_/debug',
                'type': 'stlib',
                'name': 'fooutil',
            },
        },

.. _buildconf-edep-params-export-includes:

export-includes
"""""""""""""""""""""
    A list of paths with 'includes' for C/C++/D/Fortran compilers to export from
    the dependency project for all build tasks which depend on the current dependency.
    Paths should be relative to the :ref:`startdir<buildconf-startdir>` or
    absolute but last variant is not recommended.

    If paths contain spaces and all these paths are listed
    in one string then each such a path must be in quotes.

rules
"""""""""""""""""""""
    A :ref:`dict<buildconf-dict-def>` with descriptions of rules to produce
    targets files of dependency. Each rule has own reserved name and
    parameters to run. The rule names that allowed to use are:
    ``configure``, ``build``, ``test``, ``clean``, ``install``, ``uninstall``.

    The parameters for each rule can a string with a command line to run or
    a dict with attributes:

    :cmd:
        A command line to run. It can be any suitable command line.

    :cwd:
        A working directory where to run ``cmd``. By default it's
        the :ref:`rootdir<buildconf-edep-params-rootdir>`.
        This path can be relative to the :ref:`startdir<buildconf-startdir>` or absolute.

    :env:
        Environment variables for ``cmd``. It's a ``dict`` where each
        key is a name of variable and value is a value of env variable.

    :timeout:
        A timeout for ``cmd`` in seconds. By default there is no timeout.

    :shell:
        If shell is True, the specified command will be executed through
        the shell.  By default it is False.
        In some cases it can be set to True by ZenMake even though you
        set it to False.

    :trigger:
        A dict that describes conditions to run the rule.
        If any configured trigger returns True then the rule will be run.
        You can configure one or more triggers for each rule.
        ZenMake supports the following types of trigger:

        :always:
            If it's True then the rule will be run always. If it's False and
            no other triggers then the rule will not be run automatically.

        :paths-exist:
            This trigger returns True only if configured paths exist on
            a file system. You can set paths as a string, list of strings or as
            a dict like for config task parameter
            :ref:`source<buildconf-taskparams-source>`.

            Examples in Python format:

            .. code-block:: python

                'trigger': {
                    'paths-exist' : '/etc/fstab',
                }

                'trigger': {
                    'paths-exist' : ['/etc/fstab', '/tmp/somefile'],
                }

                'trigger': {
                    'paths-exist' : dict(
                        startdir = ../foo-lib,
                        incl = '**/*.label',
                    ),
                }

        :paths-dont-exist:
            This trigger is the same as ``paths-exist`` but returns True if
            configured paths don't exist.

        :env:
            This trigger returns True only if all configured environment variables
            exist and equal to configured values. Format is simple:
            it's a ``dict`` where each key is a name of variable and value
            is a value of environment variable.

        :no-targets:
            If it is True this trigger returns True only if any of target files
            for current dependency doesn't exist. It can be useful to detect
            the need to run 'build' rule.
            This trigger can not be used in ZenMake command 'configure'.

        :func:
            This trigger is a custom python function that must return True or False.
            This function gets the following parameters as arguments:

            :zmcmd:
                It's a name of the current ZenMake command that has been used
                to run the rule.

            :targets:
                A list of configured/detected targets. It's can be None if rule
                has been run from command 'configure'.

            It's better to use `**kwargs` in this function because some new
            parameters can be added in the future.

            This trigger can not be used in YAML buildconf file.

        .. note::
            For any non-ZenMake dependency there are following
            default triggers for rules:

            configure: { 'always' : True }

            build: { 'no-targets' : True }

            Any other rule: { 'always' : False }

        .. note::
            You can use command line option ``-E``/``--force-edeps`` to run
            rules for external dependencies without checking triggers.

    :zm-commands:
        A list with names of ZenMake commands in which selected rule will be run.
        By default each rule can be run in the ZenMake command with the same name only.
        For example, rule 'configure' by default can be run with the command
        'configure' and rule 'build' with the command 'build', etc.
        But here you can set up a different behavior.

.. _buildconf-edep-params-buildtypes-map:

buildtypes-map
"""""""""""""""""""""
    This parameter is used only for external dependencies which are other
    ZenMake projects. By default ZenMake uses value of current ``buildtype``
    for all such dependencies to run rules but in some cases names of buildtype
    can be not matched. For example, current project can have buildtypes
    ``debug`` and ``release`` but project from dependency can have
    buildtypes ``dbg`` and ``rls``. In this case
    you can use this parameter to set up the map of these buildtype names.

    Example in Python format:

    .. code-block:: python

        buildtypes-map: {
            'debug'   : 'dbg',
            'release' : 'rls',
        }


Some examples can be found in the directory 'external-deps'
in the repository `here <repo_demo_projects_>`_.
