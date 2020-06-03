.. include:: global.rst.inc
.. highlight:: python
.. _buildconf:

Build config
============

ZenMake uses build configuration file with name ``buildconf.py`` or
``buildconf.yaml``. First variant is a regular python file and second is
a YAML file. ZenMake doesn't use both files in one directory at the same time.
If both files exist in one directory then only ``buildconf.py`` will be used.
Common name ``buildconf`` is used in this manual.

The format for both config files is the same. YAML variant is a little more
readable but in python variant you can add a custom python code if you wish.

Simplified scheme of buildconf is:

.. parsed-literal::

    startdir_ = path
    buildroot_ = path
    realbuildroot_ = path
    project_ = { ... }
    :ref:`buildconf-features` = { ... }
    options_ = { ... }
    conditions_ = { ... }
    tasks_ = { name: :ref:`task parameters<buildconf-taskparams>` }
    buildtypes_ = { name: :ref:`task parameters<buildconf-taskparams>` }
    toolchains_ = { name: parameters }
    platforms_ = { name: parameters }
    matrix_ = [ { for: {...}, set: :ref:`task parameters<buildconf-taskparams>` }, ... ]
    :ref:`buildconf-subdirs` = []
    dependencies_ = { ... }

.. _buildconf-dict-def:

Where symbols '{}' mean an associative array/dictionary and symbols '[]'
mean a list. In python notation '{}' is known as dictionary. In some other
languages it's called an associative array including YAML (Of course YAML is not
programming language but it's markup language). For shortness it's called
a ``dict`` here.

Not all variables are required in the scheme above but buildconf can not be
empty. All variables have reserved names and they all are described here.
Other names in buildconf are just ignored by ZenMake if present and it means
they can be used for some custom purposes.

.. note::

    **About paths in general.**

    You can use native paths but it's recommended to use wherever possible
    POSIX paths (Symbol ``/`` is used as a separator in a path).
    With POSIX paths you will ensure the same paths on
    different platforms/operation systems. POSIX paths will be
    converted into native paths automatically, but not vice versa.
    For example, path 'my/path' will be converted into 'my\\path' on Windows.
    Also it's recommended to use relative paths wherever possible.

Below is the detailed description of each buildconf variable.

.. _buildconf-startdir:

startdir
""""""""
    A start path for all paths in a buildconf.
    It is ``.`` by default. The path can be absolute or relative to directory
    where current buildconf file is located. It means by default all other
    relative paths in the current buildconf file are considered as the paths
    relative to directory with the current buildconf file.
    But you can change this by setting different value to this variable.

.. _buildconf-buildroot:

buildroot
"""""""""
    A path to the root of a project build directory. By default it is
    directory 'build' in the directory with the top-level buildconf file of
    the project. Path can be absolute or relative to the startdir_.
    It is important to be able to remove the build
    directory safely, so it should never be given as ``.`` or ``..``.

    .. note::
      If you change value of ``buildroot`` with already using/existing
      build directory then ZenMake will not touch previous build directory.
      You can remove previous build directory manually or run
      command ``distclean`` before changing of ``buildroot``.
      ZenMake can not do it because it stores all
      meta information in current build directory and if you change this
      directory it loses all this information.

      This can be changed in the future by storing extra information in some
      other place like user home directory but now it is.

realbuildroot
"""""""""""""
    A path to the real root of a project build directory and by default it is
    equal to value of ``buildroot``. It is optional parameter and if
    ``realbuildroot`` has different value from ``buildroot`` then
    ``buildroot`` will be symlink to ``realbuildroot``. Using ``realbuildroot``
    has sense mostly on linux where '/tmp' is usually on tmpfs filesystem
    nowadays and it can used to make building in memory. Such a way can improve
    speed of building. Note that on Windows OS process of ZenMake needs to be
    started with enabled "Create symbolic links" privilege and usual user
    doesn't have a such privilege.
    Path can be absolute or relative to the startdir_.
    It is important to be able to remove the build directory safely,
    so it should never be given as ``.`` or ``..``.

project
"""""""
    A `dict <buildconf-dict-def_>`_ with some parameters for the project.
    Supported values:

    :name: The name of the project. It's name of the top-level startdir_
           directory by default.
    :version: The version of the project. It's empty by default.
              It's used as default value for ``ver-num`` field if not empty.

.. _buildconf-features:

features
""""""""
    A `dict <buildconf-dict-def_>`_ array with some features.
    Supported values:

    :autoconfig: Execute the command ``configure`` automatically in
                 the command ``build`` if it's necessary.
                 It's ``True`` by default. Usually you don't need to change
                 this value.

    :monitor-files: Set extra file paths to check changes in them. You can use
                    additional files with your buildconf file(s). For example
                    it can be extra python module with some tools. But in this
                    case ZenMake doesn't know about such files when it checks
                    buildconf file(s) for changes to detect if it must call
                    command ``configure`` for feature ``autoconfig``. You
                    can add such files to this variable and ZenMake will check
                    them for changes as it does so for regular buildconf file(s).

                    If paths contain spaces and all these paths are listed
                    in one string then each such a path must be in quotes.

    :hash-algo: Set hash algorithm to use in ZenMake. It can be ``sha1`` or
                ``md5``. By default ZenMake uses sha1 algorithm to control
                changes of config/built files and for some other things.
                Sha1 has much less collisions than md5
                and that's why it's used by default. Modern CPUs often has support
                for this algorithm and sha1 show better or almost the same
                performance than md5 in this cases. But in some cases md5 can be
                faster and you can set here this variant. However, don't expect big
                difference in performance of ZenMake. Also, if a rare
                "FIPS compliant" build of Python is used it's always sha1 anyway.

    :db-format: Set format for internal ZenMake db/cache files.
                Use one of possible values: 'py', 'pickle', 'msgpack'.

                The value 'py' means text file with python syntax. It's not fastest
                format but it's human readable one.

                The value 'pickle' means python pickle binary format. It has
                good performance and python always supports this format.

                The value 'msgpack' means msgpack binary
                format by using python module 'msgpack'. Using of this format can
                decrease ZenMake overhead in building of some big projects because
                it has best performance among all supported formats.
                It can be set only for python 3.x because the extension module
                in msgpack was dropped for python 2.x and using of pure python
                implementation has no sense. If it is set for python 2.x or
                if package 'msgpack' doesn't exist in the current system then
                it will be replaced by value 'pickle'.
                Note: ZenMake doesn't try to install package 'msgpack'.
                This package must be installed in some other way.

                The default value is 'pickle'.

    :provide-dep-targets: Provide target files of
                :ref:`external dependencies<dependencies-external>`
                in the :ref:`buildroot<buildconf-buildroot>` directory.
                It is useful to run built files from the build directory without
                the need to use such a thing as LD_LIBRARY_PATH for each dependency.
                Only existing and used target files are provided.
                Static libraries are also ignored because they are not needed
                to run built files.
                On Windows ZenMake copies these files while on other OS
                (Linux, MacOS, etc) it makes symlinks.

                It's ``False`` by default.

    :build-work-dir-name: Set name of work directory which is used mostly for
            object files during compilation. This directory seperates
            resulting target files from other files in a buildtype directory to
            avoid file/directory conflicts. Usually you don't need to set this
            parameter until some target name has conflict with default value of
            this parameter. The default value is ``@bld``.

options
""""""""
    A `dict <buildconf-dict-def_>`_ array with default values for command
    line options. It can be any existing command line option that ZenMake has.
    If you want to set option for selected commands then you can set in format
    of a `dict <buildconf-dict-def_>`_ where key is a name of command or
    special value 'any' which means any command. If some command doesn't have
    selected option then it will be ignored.
    Example in YAML format:

    .. code-block:: yaml

        options:
          verbose: 1
          jobs : { build : 4 }
          progress :
            any: false
            build: true

    .. note::
        Selected command here is a command that is used on command line.
        It means if you set some option for command ``build`` and zenmake calls
        the command ``configure`` before this command itself then this option will
        be applied for both ``configure`` and ``build``. In other words it's
        like you run this command with this option on command line.

.. _buildconf-conditions:

conditions
"""""""""""
    A `dict <buildconf-dict-def_>`_ with conditions for
    :ref:`selectable parameters<buildconf-select>`.

.. _buildconf-tasks:

tasks
"""""
    A `dict <buildconf-dict-def_>`_ with build tasks. Each task has own
    unique name and :ref:`parameters<buildconf-taskparams>`. Name of task can
    be used as dependency id for other build tasks. Also this name is used as a
    base for resulting target file name if parameter ``target`` is not set in
    :ref:`task parameters<buildconf-taskparams>`.
    In this variable you can set up build parameters particularly for each build task.
    Example in YAML format:

    .. code-block:: yaml

        tasks:
          mylib :
            # some task parameters
          myexe :
            # some task parameters
            use : mylib

    .. note::
        Parameters in this variable can be overridden by parameters in
        buildtypes_ and matrix_.

    .. note::
        Name of a task can not contain symbol ``:``. You can use
        parameter ``target`` if you want to have this symbol in
        resulting target file names.

.. _buildconf-buildtypes:

buildtypes
""""""""""
    A `dict <buildconf-dict-def_>`_ with build types like ``debug``, ``release``,
    ``debug-gcc`` and so on. Here is also a special value with name ``default``
    that is used to set default build type if nothing is specified. Names of
    these build types are just names, they can be any name but not ``default``.
    Also you should remember that these names are used as
    directory names. So don't use
    incorrect symbols if you don't want a problem with it.

    This variable can be empty or absent. In this case current buildtype is
    always just an empty string.

    Possible parameters for each build type are described in
    :ref:`task parameters<buildconf-taskparams>`.
    Special value ``default`` must be name of one of the build types.
    Example in YAML format:

    .. code-block:: yaml

        buildtypes:
          debug        : { toolchain: auto-c++ }
          debug-gcc    : { toolchain: g++, cxxflags: -fPIC -O0 -g }
          release-gcc  : { toolchain: g++, cxxflags: -fPIC -O2 }
          debug-clang  : { toolchain: clang++, cxxflags: -fPIC -O0 -g }
          release-clang: { toolchain: clang++, cxxflags: -fPIC -O2 }
          debug-msvc   : { toolchain: msvc, cxxflags: /Od /EHsc }
          release-msvc : { toolchain: msvc, cxxflags: /O2 /EHsc }
          default: debug

    .. note::
        Parameters in this variable can override parameters in tasks_ and
        can be overridden by parameters in matrix_.

.. _buildconf-toolchains:

toolchains
""""""""""
    A `dict <buildconf-dict-def_>`_ with custom toolchain setups. It's useful
    for simple cross builds for example, or for custom settings for existing
    toolchains. Each value has unique name and parameters. Parameters are also
    dict with names of environment variables and
    special name ``kind`` that is used for specifying type of
    toolchain/compiler. Environment variables are usually such variables as
    ``CC``, ``CXX``, ``AR``, etc that is used to specify
    name or path to existing toolchain/compiler. Path can be absolute or
    relative to the startdir_. But also it can be variables ``CFLAGS``,
    ``CXXFLAGS``, etc. Names of toolchains from this
    variable can be used as value for parameter ``toolchain``
    in :ref:`task parameters<buildconf-taskparams>`.

    Example in YAML format:

    .. code-block:: yaml

        toolchains:
          custom-g++:
            kind : auto-c++
            CXX  : custom-toolchain/gccemu/g++
            AR   : custom-toolchain/gccemu/ar
          custom-clang++:
            kind : clang++
            CXX  : custom-toolchain/clangemu/clang++
            AR   : custom-toolchain/clangemu/llvm-ar
          g++:
            LINKFLAGS : -Wl,--as-needed

platforms
"""""""""
    A `dict <buildconf-dict-def_>`_ with some settings specific to platforms.
    It's important variable if your project should be built on more than one
    platform. Each value must have name of platform with value of 2 parameters:
    ``valid`` and ``default``. Parameter ``valid`` is a string or list of
    valid/supported buildtypes_ for selected platform and optional parameter
    ``default`` specifies default buildtype as one of valid buildtypes.
    Also parameter ``default`` overrides parameter ``default``
    from buildtypes_ for selected platform.

    Valid platform names: ``linux``, ``windows``, ``darwin``, ``freebsd``,
    ``openbsd``, ``sunos``, ``cygwin``, ``msys``, ``riscos``, ``atheos``,
    ``os2``, ``os2emx``, ``hp-ux``, ``hpux``, ``aix``, ``irix``.

    .. note::
        Only ``linux``, ``windows``, ``darwin`` are tested.

    Example in YAML format:

    .. code-block:: yaml

        platforms:
          linux :
            valid : [debug-gcc, debug-clang, release-gcc, release-clang ]
            default : debug-gcc
          # Mac OS
          darwin :
            valid : [debug-clang, release-clang ]
            default : debug-clang
          windows :
            valid : [debug-msvc, release-msvc ]
            default : debug-msvc

.. _buildconf-matrix:

matrix
""""""
    This variable describes extra/alternative way to set up build tasks.
    It's a list of `dicts <buildconf-dict-def_>`_ with variables:
    ``set`` and ``for`` and/or ``not-for``.
    Variables ``for`` and ``not-for`` describe conditions for parameters
    in variable ``set``. The variable ``for`` is like a ``if a`` and the variable
    ``not-for`` is like a ``if not b`` where ``a`` and ``b`` are some conditions.
    When both of them exist in the same item
    they are like a ``if a and if not b``. In the case of the same condition
    in both of them the variable ``not-for`` has higher priority.
    Each this variable is a dict with one or more keys:

    :task:      Build task name or list of build task names.
                It can be existing task(s) from tasks_ or new.
    :platform:  Name of platform or list of them. Valid values are the same
                as for platforms_.
    :buildtype: Build type or list of build types.
                It can be existing build type(s) from buildtypes_ or new.

    Variable ``set`` has value of the :ref:`task parameters<buildconf-taskparams>`
    with additional variable ``default-buildtype``.

    Other features of matrix:

    - If some variable is not specified in ``for``/``not-for`` it means that
      this is for all possible values of this kind of condition. For example
      if no ``task`` it means for all existing tasks.
    - Matrix overrides all values defined in tasks_ and buildtypes_
      if they are matching.
    - Items in ``set`` with the same names and the same conditions in ``for``
      and ``not-for`` override items defined before.
    - When ``set`` is empty or not defined it does nothing.

    You can use only ``matrix`` without tasks_ and buildtypes_ if you want.

    Example in YAML format:

    .. code-block:: yaml

        matrix:
          - for: {} # for all
            set: { includes: '.', rpath : '.', }

          - for: { task: shlib shlibmain }
            set: { features: cxxshlib }

          - for: { buildtype: debug-gcc release-gcc, platform: linux }
            set:
              toolchain: g++
              linkflags: -Wl,--as-needed
              default-buildtype: release-gcc

          - for: { buildtype: release-gcc }
            not-for : { platform : windows }
            set: { cxxflags: -fPIC -O3 }

          - for: { buildtype: [debug-clang, release-clang], platform: linux darwin }
            set: { toolchain: clang++ }

.. _buildconf-subdirs:

subdirs
"""""""
    This variable controls including buildconf files from other sub directories
    of the project.

    - If it is list of paths then ZenMake will try to use this list as paths
      to sub directories with the buildconf files and will use all found ones.
      Paths can be absolute or relative to the :ref:`startdir<buildconf-startdir>`.
    - If it is an empty list or just absent at all
      then ZenMake will not try to use any
      sub directories of the project to find buildconf files.

    Example in Python format:

    .. code-block:: python

        subdirs = [
            'libs/core',
            'libs/engine',
            'main',
        ]

    Example in YAML format:

    .. code-block:: yaml

        subdirs:
            - libs/core
            - libs/engine
            - main

    See some details :ref:`here<dependencies-subdirs>`.

.. _buildconf-dependencies:

dependencies
""""""""""""
    A `dict <buildconf-dict-def_>`_ with configurations of external non-system
    dependencies. Each such a dependency has own unique name which can be used in
    task parameter :ref:`use<buildconf-taskparams-use>`.

    See full description of parameters :ref:`here<buildconf-dep-params>`.
    Description of external dependencies is :ref:`here<dependencies-external>`.

.. note::

    More examples of buildconf files can be found in repository
    `here <repo_demo_projects_>`_.