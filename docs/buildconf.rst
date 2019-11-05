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
    options_ = { ... }
    tasks_ = { name: taskparams_ }
    buildtypes_ = { name: taskparams_ }
    toolchains_ = { name: parameters }
    platforms_ = { name: parameters }
    matrix_ = [ { for: {...}, set: taskparams_ }, ... ]

.. _buildconf-dict-def:

Where symbols '{}' mean an associative array/dictionary and symbols '[]'
mean a list. In python '{}' is known as dictionary. In some other languages
it's called an associative array including YAML (Of course YAML is not
programming language but it's markup language). For shortness it's called
a ``dict`` here.

Not all variables are required in the scheme above but buildconf can not be
empty. All variables have reserved names. Any other names in buildconf are
just ignored by ZenMake if present and it means they can be used for
some custom purposes.

.. note::

    **About paths in general.**

    You can use native paths but it's recommended to use wherever possible
    POSIX paths (Symbol ``/`` is used as a separator in a path).
    With POSIX paths you will ensure the same paths on
    different platforms/operation systems. POSIX paths will be
    converted into native paths automatically. But not vice versa.
    For example, path 'my/path' will be converted into 'my\\path' on Windows.
    Also it's recommended to use relative paths wherever possible.

Below is the detailed description of each buildconf variable.

buildroot
"""""""""
    A path to the root of a project build directory. By default it is
    directory 'build' in the project root path. Path can be absolute or
    relative to directory where buildconf file is located. It is important
    to be able to remove the build directory safely, so it should never
    be given as ``.`` or ``..``.

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
    doesn't have a such privilege. Path can be absolute or relative to
    directory where buildconf file is located. It is important to be able to
    remove the build directory safely, so it should never be given as ``.``
    or ``..``.

srcroot
"""""""
    A path to the root directory for all source files to compile.
    By default it's root directory of the project (see ``root`` in the
    variable project_). The path can be absolute or relative to directory
    where buildconf file is located.

project
"""""""
    A `dict <buildconf-dict-def_>`_ with some parameters for the project.
    Supported values:

    :name: The name of the project. It's name of the project directory by default.
    :version: The version of the project. It's empty by default.
              It's used as default value for ``ver-num`` field if not empty.
    :root: A path to the root of the project. It's ``.`` by default and in most
           cases it shouldn't be changed. The path can be absolute or relative to
           directory where buildconf file is located.

features
""""""""
    A `dict <buildconf-dict-def_>`_ array with some features.
    Supported values:

    :autoconfig: Execute the command ``configure`` automatically in
                 the command ``build`` if it's necessary.
                 It's ``True`` by default. Usually you don't need to change
                 this value.

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

tasks
"""""
    A `dict <buildconf-dict-def_>`_ with build tasks. Each task has own
    unique name and parameters. Name of task can be used as dependency id for
    other build tasks. Also this name is used as a base for resulting target
    file name if parameter ``target`` is not set in task parameters.
    Task parameters are described in taskparams_. In this variable you can set
    up build parameters particularly for each build task.
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

buildtypes
""""""""""
    A `dict <buildconf-dict-def_>`_ with build types like ``debug``, ``release``,
    ``debug-gcc`` and so on. Here is also a special value with name ``default``
    that is used to set default build type if nothing is specified. Names of
    these build types are just names, they can be any except ``default``
    but remember that these names are used as directory names. So don't use
    incorrect symbols if you don't want a problem with it.

    This variable can be empty or absent. In this case current buildtype is
    always just an empty string.

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
        can be overridden by parameters in matrix_.

toolchains
""""""""""
    A `dict <buildconf-dict-def_>`_ with custom toolchains setups. It's useful
    for simple cross builds for example. In common case you don't need it.
    Each value has unique name and parameters. Parameters are also
    dict with names of environment variables and
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

matrix
""""""
    This variable describes extra/alternative way to set up build tasks.
    It's a list of `dicts <buildconf-dict-def_>`_ with two variables:
    ``set`` and ``for``. Variable ``for`` describes conditions for parameters
    in variable ``set``. Variable ``for`` is a dict with variables:

    :task:      Build task name or list of build task names.
                It can be existing task(s) from tasks_ or new.
    :platform:  Name of platform or list of them. Valid values are the same
                as for platforms_.
    :buildtype: Build type or list of build types.
                It can be existing build type(s) from buildtypes_ or new.

    Variable ``set`` has value of the taskparams_ with additional
    variable ``default-buildtype``.

    Other features of matrix:

    - If some variable is not specified in ``for`` it means that this is for
      all possible values of this kind of condition. For example if no ``task``
      it means for all existing tasks.
    - Matrix overrides all values defined in tasks_ and buildtypes_
      if they are matching.
    - Items in ``set`` with the same names and the same conditions in ``for``
      override items defined before.
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

          - for: { buildtype: release-gcc, platform: linux }
            set: { cxxflags: -fPIC -O3 }

          - for: { buildtype: [debug-clang, release-clang], platform: linux darwin }
            set: { toolchain: clang++ }

taskparams
""""""""""
    It's not variable name. It's a `dict <buildconf-dict-def_>`_ as a some
    collection of build task parameters for one build task. This collection
    is used in tasks_, buildtypes_ and matrix_.
    And it's core element of the buildconf.

    .. _buildconf-taskparams-features:

    features
        It describes type of the build task. Can be one value or list
        of values. Supported values:

        :cstlib:
            Means that result of the task is a static library for C code.
        :cshlib:
            Means that result of the task is a shared library for C code.
        :cprogram:
            Means that result of the task is an executable file for C code.
        :cxxstlib:
            Means that result of the task is a static library for C++ code.
        :cxxshlib:
            Means that result of the task is a shared library for C++ code.
        :cxxprogram:
            Means that result of the task is an executable file for C++ code.
        :c:
            Means that the task has a C code. Optional.
        :cxx:
            Means that the task has a C++ code. Optional.
        :stlib:
            Means that result of the task is a static library. Type of code
            is detected by file extensions found in
            `source <buildconf-taskparams-source_>`_.
        :shlib:
            Means that result of the task is a shared library. Type of code
            is detected by file extensions found in
            `source <buildconf-taskparams-source_>`_.
        :program:
            Means that result of the task is an executable file. Type of code
            is detected by file extensions found in
            `source <buildconf-taskparams-source_>`_.
        :runcmd:
            Means that the task has parameter ``run`` and should run some
            command. It's optional because ZenMake detects this feature
            automatically by presence of the ``run`` in task parameters.
            You need to set it explicitly only if you want to try to run
            \*program task without parameter ``run``.
        :test:
            Means that the task is a test. More details about
            tests :ref:`here<buildtests>`. It is not needed to add ``runcmd``
            to this feature because ZenMake adds ``runcmd`` itself if necessary.

        Some features can be mixed. For example ``cxxprogram`` can be mixed
        with ``c`` for C/C++ mixed build tasks. But ``cxxshlib`` cannot be
        mixed for example with ``cxxprogram``. Using of features ``c`` or ``cxx``
        doesn't make sense without \*stlib/\*shlib/\*program features.
        Features ``runcmd`` and ``test`` can be mixed with any feature.

    target
        Name of resulting file. The target will have different extension and
        name depending on the platform but you don't need to declare this
        difference explicitly. It will be generated automatically. For example
        the ``sample`` for \*shlib task will be converted into
        ``sample.dll`` on Windows and into ``libsample.so`` on Linux.
        By default it's equal to the name of the build task. So in most cases
        it is not needed to be set explicitly.

    sys-libs
        One or more names of system libraries as dependencies.
        Example:

        .. code-block:: python

            'sys-libs' : 'm rt'

    sys-lib-path
        One or more paths to find system libraries. Usually you don't need to
        set it.
        Example:

        .. code-block:: python

            'sys-lib-path' : '/usr/lib'

    rpath
        One or more paths to hard-code into the binary during
        linking time. It's ignored on platforms that do not support it.

    use
        This attribute enables the link against libraries (static or shared).
        It's used not for system libraries (see ``sys-libs``). Also it's used
        to declare dependencies between build tasks.

    ver-num
        Enforce version numbering on shared libraries. It can be used with
        \*shlib ``features`` for example. It's ignored on platforms that do
        not support it.

    includes
        Include paths are used by the C/C++ compilers for finding headers.
        Paths should be relative to srcroot_ or absolute but last variant is
        not recommended.

    export-includes
        If it's True then it exports value of ``includes`` for all buld tasks
        depending on the current task. Also it can be one or more paths
        for explicit exporting. By default it's False.

    .. _buildconf-taskparams-source:

    source
        One or more source files for compiler/toolchain.
        It can be string with path or list of such strings or
        a `dict <buildconf-dict-def_>`_.
        Type ``dict`` is used for Waf_ ``ant_glob`` function. Format of patterns
        for ``ant_glob`` you can find on https://waf.io/book/.
        Main details from there:

            - Patterns may contain wildcards such as \* or \?, but they are
              `Ant patterns <https://ant.apache.org/manual/dirtasks.html>`_,
              not regular expressions.
            - The symbol ``**`` enable recursion. Complex folder hierarchies may
              take a lot of time, so use with care.

        So such a ``dict`` can contain fields:

            :include:
                Ant pattern or list of patterns to include, required field.
            :exclude:
                Ant pattern or list of patterns to exclude, optional field.
            :ignorecase:
                Ignore case while matching (False by default), optional field.

        Any path or pattern should be relative to srcroot_.

        Examples in python format:

        .. code-block:: python

            # just one file
            'source' : 'test.cpp'

            # list of two files
            'source' : 'main.c about.c'
            'source' : ['main.c', 'about.c'] # the same result

            # get all *.cpp files in 'srcroot' recursively
            'source' :  dict( include = '**/*.cpp' )
            # or
            'source' :  { 'include': '**/*.cpp' }

            # get all *.cpp files in 'srcroot'/mylib recursively
            'source' :  dict( include = 'mylib/**/*.cpp' )

        Examples in YAML format:

        .. code-block:: yaml

            # list of two files
            source : main.c about.c
            # or
            source : [main.c, about.c]

            # get all *.cpp files in 'srcroot'/mylib recursively
            source: { include: 'mylib/**/*.cpp' }
            # or
            source:
              include: 'mylib/**/*.cpp'

    toolchain
        Name of toolchain/compiler to use in the task. It can be any system
        compiler that is supported by Waf or toolchain from custom toolchains_.
        There are also the special names for autodetecting in format
        ``auto-*`` where ``*`` is programming language, for example
        ``auto-c`` or ``auto-c++``.

        | Known names for C: ``gcc``, ``clang``, ``msvc``, ``icc``, ``xlc``,
                             ``suncc``, ``irixcc``.
        | Known names for C++: ``g++``, ``clang++``, ``msvc``, ``icpc``,
                               ``xlc++``, ``sunc++``.
        | Known names for Assembler: ``gas``, ``nasm``.

        .. note::

            If no toolchain was given ZenMake tries to set ``auto-*`` itself by
            values of `features <buildconf-taskparams-features_>`_. But
            feature with autodetecting of language by file extensions cannot
            be used for autodetecting of correct ``auto-*``. For example with
            ``cxxshlib`` ZenMake can set ``auto-c++`` itself but not
            with ``shlib``.

    cflags
        One or more compiler flags for C.

    cxxflags
        One or more compiler flags for C++.

    asflags
        One or more compiler flags for Assembler.

    cppflags
        One or more compiler flags added at the end of compilation commands.

    linkflags
        One or more linker flags for C/C++.

    aslinkflags
        One or more linker flags for Assembler.

    defines
        One or more defines for C/C++/Assembler.

    export-defines
        If it's True then it exports value of ``defines`` for all buld tasks
        depending on the current task. Also it can be one or more defines
        for explicit exporting. By default it's False.

    install-path
        String representing the installation path for the output files.
        It's used in commands ``install`` and ``uninstall``.
        To disable installation, set it to False, None or empty string.
        If it's absent then general values of ``${PREFIX}``, ``${BINDIR}``
        and ``${LIBDIR}`` will be used to detect path.
        You can use variables ``${PREFIX}``, ``${BINDIR}``, ``${LIBDIR}`` here
        like this:

        .. code-block:: python

            'install-path' : '${PREFIX}/exe'

    .. _buildconf-taskparams-run:

    run
        A `dict <buildconf-dict-def_>`_ with parameters to run something in
        the task. It' used with task features ``runcmd`` and ``test``.

        :cmd:
            Command line to run. It can be any suitable command line.
            For convenience special environment variable ``PROGRAM`` can be
            used. This variable contains the absolute path to resulting
            target file of the current task.
            For python variant of buildconf it can be python function as well.
            It this case such a function gets one argument as a python dict
            with parameters:

            :taskname:
                Name of current build task
            :projectroot:
                Root directory of the project
            :srcroot:
                Root directory of the project sources
            :buildroot:
                Root directory for building
            :buildout:
                Directory for build target(s)
            :buildtype:
                Current buildtype
            :target:
                Absolute path to resulting target. It may not be existing.
            :waftask:
                Object of Waf class Task. It's for advanced use.

        :cwd:
            Working directory where to run ``cmd``. By default it's build
            directory for current buildtype. Path can be absolute or
            relative to `project root <project_>`_.
        :env:
            Environment variables for ``cmd``. It's a ``dict`` where each
            key is a name of variable and value is a value of env variable.
        :timeout:
            Timeout for ``cmd`` in seconds. It works only when ZenMake is run
            with python 3. By default there is no timeout.
        :shell:
            If shell is True, the specified command will be executed through
            the shell.  By default to avoid some common problems it is True.
            But in many cases it's safe to set False.
            In this case it avoids some overhead of using shell.
            In some cases it can be set to True by ZenMake/Waf even though you
            set it to False.
        :repeat:
            Just amount of running of ``cmd``. It's mostly for tests.
            By default it's 1.

        Examples in python format:

        .. code-block:: python

            'echo' : {
                'run' : { 'cmd' : "echo 'say hello'" },
            },

            'test.py' : {
                'run'      : {
                    'cmd'   : 'python tests/test.py',
                    'cwd'   : '.',
                    'env'   : { 'JUST_ENV_VAR' : 'qwerty', },
                    'shell' : False,
                },
                'conftests'  : [ dict(act = 'check-programs', names = 'python'), ]
            },

            'shlib-test' : {
                'features' : 'cxxprogram test',
                # ...
                'run'      : {
                    'cmd'     : '${PROGRAM} a b c',
                    'env'     : { 'ENV_VAR1' : '111', 'ENV_VAR2' : 'false'},
                    'repeat'  : 2,
                    'timeout' : 10, # in seconds, Python 3 only
                    'shell'   : False,
                },
            }

    conftests
        A list of configuration tests. An item ih the list can be a ``dict``
        where ``act`` specifies some type of configuration test. Another
        possible value of the item is a python function that must return
        True/False on Success/Failure. Arguments for such a function can be
        absent or: ``task``, ``buildtype``. These tests are called on
        **configure** step (command **configure**).

        These configuration tests in ``dict`` format:

            ``act`` = ``check-programs``
                Check existence of programs from list in the ``names``.
                Parameter ``paths`` can be used to set paths to find
                these programs, but usually you don't need to use it.

            ``act`` = ``check-sys-libs``
                Check existence of all system libraries from
                task parameter ``sys-libs``.

            ``act`` = ``check-headers``
                Check existence of C/C++ headers from list in the ``names``.

            ``act`` = ``check-libs``
                Check existence of the system libraries from list in
                the ``names``. If ``autodefine`` is set to True it generates
                ``C/C++ define name`` like ``HAVE_LIB_SOMELIB``.

            ``act`` = ``check-by-pyfunc``
                Check by python function. It'a another way to use python
                function for checking. In this way you can use parameter
                ``mandatory``.

            ``act`` = ``check``
                Just proxy to Waf common method ``check``.

            ``act`` = ``write-config-header``
                After all the configuration tests are executed, write a
                configuration header in the build directory.
                The configuration header is used to limit the size of the
                command-line. By default file name is ``<task name>_config.h``.
                Parameter ``guard`` can be used to change C/C++ header guard.
                In your C/C++ code you can just include this file like that:

                .. code-block:: c++

                    #include "yourconfig.h"

                You can override file name by using parameter ``file``.

        Any configuration test excepting ``write-config-header`` has parameter
        ``mandatory`` which is True by default.

        Example in python format:

        .. code-block:: python

            def check(task, buildtype):
                # some checking
                return True

            'myapp' : {
                'features'   : 'cxxshlib',
                'sys-libs'   : ['m', 'rt'],
                # ...
                'conftests'  : [
                    # do checking in function 'check'
                    check,
                    # Check libs from param 'sys-libs'
                    dict(act = 'check-sys-libs'),
                    dict(act = 'check-headers', names = 'cstdio', mandatory = True),
                    dict(act = 'check-headers', names = 'cstddef stdint.h', mandatory = False),
                    # Each lib will have define 'HAVE_LIB_<LIBNAME>' if autodefine = True
                    dict(act = 'check-libs', names = 'pthread', autodefine = True,
                                mandatory = False),
                    dict(act = 'check-programs', names = 'python'),

                    #dict(act = 'write-config-header', file = 'myapp_config.h')
                    dict(act = 'write-config-header'),
                ],
            }

    normalize-target-name
        Convert ``target`` name to ensure the name is suitable for file name
        and has not any potential problems.
        It replaces all space symbols for example. Experimental.
        By default it is False.

    object-file-counter
        Counter for the object file extension. By default it's 1.

.. note::

    More examples of buildconf files can be found in repository
    `here <repo_demo_projects_>`_.