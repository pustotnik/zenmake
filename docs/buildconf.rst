.. include:: global.rst.inc
.. highlight:: python
.. _buildconf:

Build config
============

ZenMake uses build configuration file with name ``buildconf.py`` or
``buildconf.yaml``. First variant is a regular python file and second is
a YAML file. ZenMake doesn't use both files at the same time. If both files
exist in the root of a project then only ``buildconf.py`` will be used.
So common variant ``buildconf`` is used in this manual.

The format for both config files are the same. YAML variant is a little more
readable but in python variant you can add a custom python code if you wish.

Simplified scheme of buildconf:

.. parsed-literal::

    buildroot_ = path
    realbuildroot_ = path
    srcroot_ = path
    project_ = { ... }
    features_ = { ... }
    tasks_ = { name: taskparams_ }
    buildtypes_ = { name: taskparams_ }
    toolchains_ = { name: parameters }
    platforms_ = { name: parameters }
    matrix_ = [ { for: {...}, set: taskparams_ }, ... ]

Where symbols '{}' mean an associative array/dictionary and symbols '[]'
mean a list.

There is only one required configuration variable and it's ``buildtypes``. But
you don't want to set up only this variable. All other variables are optional
but have reserved names. Any other names in buildconf are just ignored
by ZenMake if present and it means they can be used for some custom purposes.

Below is the detailed description of each buildconf variable.

buildroot
"""""""""
    A path to the root of a project build directory. By default it is
    directory 'build' in the project root path. Path can be absolute or
    relative to directory where buildconf file is located.

realbuildroot
"""""""""""""
    A path to the real root of a project build directory and by default it is
    equal to value of ``buildroot``. It is optional parameter and if
    ``realbuildroot`` has different value from ``buildroot`` then
    ``buildroot`` will be symlink to ``realbuildroot``. Using ``realbuildroot``
    has sense mostly on linux where '/tmp' is usualy on tmpfs filesystem
    nowadays and it can used to make building in memory. Such a way can improve
    speed of building. Note that on Windows OS process of ZenMake needs to be
    started with enabled "Create symbolic links" privilege and usual user
    doesn't have a such privilege. Path can be absolute or relative to
    directory where buildconf file is located.

srcroot
"""""""
    A path to the root directory for all source files to compile.
    By default it's just root path of the project. Path can be absolute or
    relative to directory where buildconf file is located.

project
"""""""
    Dictionary/associative array with some parameters for the project.
    Supported values:

    :name: The name of the project. It's 'NONAME' by default.
    :version: The version of the project. It's '0.0.0' by default.
    :root: A path to the root of the project. It's '.' by default and in most
           cases it shouldn't be changed. Path can be absolute or relative to
           directory where buildconf file is located.

features
""""""""
    Dictionary/associative array with some features.
    Supported values:

    :autoconfig: Execute the command ``configure`` automatically in
                 the command ``build`` if it's necessary.
                 It's ``True`` by default. Usually you don't need to change
                 this value.

tasks
"""""
    Dictionary/associative array with build tasks. Each task has own
    unique name and parameters. Name of task can be used as dependency id for
    other build tasks. Also this name is used as a base for resulting target
    file name if param ``target`` is not set in task parameters.
    Task parameters are described in taskparams_. In this variable you can set
    up build parameters particularly for each build task.
    Example in YAML format:

    .. code-block:: yaml

        tasks:
          mylib :
            ..
          myexe :
            use : mylib

    .. note::
        Parameters in this variable can be overrided by parameters in
        buildtypes_ and matrix_.

buildtypes
""""""""""
    Dictionary/associative array with build types like ``debug``, ``release``,
    ``debug-gcc`` and so on. Here is also a special value with name ``default``
    that is used to set default build type if nothing is specified. Names of
    these build types are just names, they can be any except ``default``
    but remember that these names are used as directory names. So don't use
    incorrect symbols if you don't want a problem with it.
    Possible parameters for each build type are described in taskparams_.
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
        can be overrided by parameters in matrix_.

toolchains
""""""""""
    Dictionary/associative array with custom toolchains setups. It's useful
    for simple cross builds for example. In common case you don't need it.
    Each value has unique name and parameters. Parameters are also
    dictionary/associative array with names of environment variables and
    special name ``kind`` that is used for specifying type of
    toolchain/compiler. Environment variables are usually such variables as
    ``CC``, ``CXX``, ``AR``, ``LINK_CXX`` and etc that is used to specify
    name or path to existing toolchain/compiler. Path can be absolute or
    relative to `project root <project_>`_. Names of toolchains from this
    variable can be used as value for parameter ``toolchain`` in taskparams_.

    Example in YAML format:

    .. code-block:: yaml

        toolchains:
          custom-g++:
            kind : auto-c++
            CXX  : custom-toolchain/gccemu/g++
            AR   : custom-toolchain/gccemu/ar
          custom-clang++:
            kind': clang++
            CXX  : custom-toolchain/clangemu/clang++
            AR   : custom-toolchain/clangemu/llvm-ar

platforms
"""""""""
    Dictionary/associative array with some settings specific to platforms.
    It's important variable if your project should be built on more than one
    platfrom. Each value must have name of platform with value of 2 parameters:
    ``valid`` and ``default``. Parameter ``valid`` is a list of valid/supported
    buildtypes_ for selected platform and optional parameter ``default`` specifies
    default buildtype as one of valid buildtypes. Also parameter ``default``
    overrides parameter ``default`` from buildtypes_ for selected platfrom.

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

matrix
""""""
    This variable describes extra/alternative way to set up build tasks.
    Features of matrix:

    - Possible keys in 'for': 'task', 'platform', 'buildtype'
    - Each value of item in 'for' can be string or list of string
    - If some key is not specified it means that this is for all possible
      values of this kind of condition. For example if no key 'task' it means
      for all existing tasks.
    - Matrix overrides all values defined previously if they are matching
    - Items in 'set' with the same names and the same conditions in 'for' can
      override items defined before
    - When 'set' is empty of not defined it does nothing

    TODO

taskparams
""""""""""
    It's not variable name. It's some collection of build task parameters that
    is used in tasks_, buildtypes_ and matrix_. And it's core element of
    the buildconf.

    TODO

More examples of buildconf files can be found in repository
`here <repo_test_projects_>`_.