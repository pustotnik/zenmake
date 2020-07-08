.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-taskparams:

Build config: task parameters
=============================

It's a :ref:`dict<buildconf-dict-def>` as a collection of build task parameters
for a build task. This collection is used in :ref:`tasks<buildconf-tasks>`,
:ref:`buildtypes<buildconf-buildtypes>` and :ref:`matrix<buildconf-matrix>`.
And it's core buildconf element.

.. _buildconf-taskparams-features:

features
"""""""""""""""""""""
    It describes type of a build task. Can be one value or list
    of values. Supported values:

    :c:
        Means that the task has a C code. Optional in most cases.
        Also it's 'lang' feature for C language.
    :cxx:
        Means that the task has a C++ code. Optional in most cases.
        Also it's 'lang' feature for C++ language.
    :d:
        Means that the task has a D code. Optional in most cases.
        Also it's 'lang' feature for D language.
    :fc:
        Means that the task has a Fortran code. Optional in most cases.
        Also it's 'lang' feature for Fortran language.
    :asm:
        Means that the task has an Assembler code. Optional in most cases.
        Also it's 'lang' feature for Assembler language.
    :<lang>stlib:
        Means that result of the task is a static library for the <lang> code.
        For example: ``cstlib``, ``cxxstlib``, etc.
    :<lang>shlib:
        Means that result of the task is a shared library for the <lang> code.
        For example: ``cshlib``, ``cxxshlib``, etc.
    :<lang>program:
        Means that result of the task is an executable file for the <lang> code.
        For example: ``cprogram``, ``cxxprogram``, etc.
    :stlib:
        Means that result of the task is a static library. It's a special
        alies where type of code
        is detected by file extensions found in
        `source <buildconf-taskparams-source_>`_.
        Be careful - it's slower than using of form <lang>stlib,
        e.g. ``cstlib``, ``cxxstlib``, etc.
        Also see note below.
    :shlib:
        Means that result of the task is a shared library. It's a special
        alies where type of code
        is detected by file extensions found in
        `source <buildconf-taskparams-source_>`_.
        Be careful - it's slower than using of form <lang>shlib,
        e.g. ``cshlib``, ``cxxshlib``, etc.
        Also see note below.
    :program:
        Means that result of the task is an executable file. It's a special
        alies where type of code
        is detected by file extensions found in
        `source <buildconf-taskparams-source_>`_.
        Be careful - it's slower than using of form <lang>program,
        e.g. ``cprogram``, ``cxxprogram``, etc.
        Also see note below.
    :runcmd:
        Means that the task has parameter ``run`` and should run some
        command. It's optional because ZenMake detects this feature
        automatically by presence of the ``run`` in task parameters.
        You need to set it explicitly only if you want to try to run
        <lang>program task without parameter ``run``.
    :test:
        Means that the task is a test. More details about
        tests :ref:`here<buildtests>`. It is not needed to add ``runcmd``
        to this feature because ZenMake adds ``runcmd`` itself if necessary.

    Some features can be mixed. For example ``cxxprogram`` can be mixed
    with ``cxx`` for C++ build tasks but it's not necessary because ZenMake
    adds ``cxx`` for ``cxxprogram`` itself. Feature ``cxxshlib`` cannot be
    mixed for example with ``cxxprogram`` in one build task because they
    are different types of build task target file. Using of such features as
    ``c`` or ``cxx`` doesn't make sense without
    \*stlib/\*shlib/\*program features in most cases.
    Features ``runcmd`` and ``test`` can be mixed with any feature.

    Examples:

    .. code-block:: python

        'features' : 'cprogram'
        'features' : 'program'
        'features' : 'cxxshlib'
        'features' : 'cxxprogram runcmd'
        'features' : 'cxxprogram test'

    .. note::

        If you use any of alieses ``stlib``, ``shlib``, ``program``
        (don't confuse with features in form of <lang>stlib,
        <lang>shlib, <lang>program) and
        patterns in `source <buildconf-taskparams-source_>`_ then you cannot
        use patterns without specifying file extension at the end of
        each pattern in the parameter 'include'.

        .. code-block:: python

            'source' :  { 'include': '**/*.cpp' }             # correct
            'source' :  { 'include': ['**/*.c', '**/*.cpp'] } # correct
            'source' :  { 'include': '**' }                   # incorrect

        If you don't use these alieses you can use any patterns.

target
"""""""""""""""""""""
    Name of resulting file. The target will have different extension and
    name depending on the platform but you don't need to declare this
    difference explicitly. It will be generated automatically. For example
    the ``sample`` for \*shlib task will be converted into
    ``sample.dll`` on Windows and into ``libsample.so`` on Linux.
    By default it's equal to the name of the build task. So in most cases
    it is not needed to be set explicitly.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-source:

source
"""""""""""""""""""""
    One or more source files for compiler/toolchain.
    It can be string with path or list of such strings or
    a :ref:`dict<buildconf-dict-def>`.
    Type ``dict`` is used for Waf_ ``ant_glob`` function. Format of patterns
    for ``ant_glob`` you can find on https://waf.io/book/.
    Most significant details from there:

        - Patterns may contain wildcards such as \* or \?, but they are
          `Ant patterns <https://ant.apache.org/manual/dirtasks.html>`_,
          not regular expressions.
        - The symbol ``**`` enable recursion. Complex folder hierarchies may
          take a lot of time, so use with care.
        - The '..' sequence does not represent the parent directory.

    So such a ``dict`` can contain fields:

        :include:
            Ant pattern or list of patterns to include, required field.
        :exclude:
            Ant pattern or list of patterns to exclude, optional field.
        :ignorecase:
            Ignore case while matching (False by default), optional field.
        :startdir:
            Start directory for patterns, optional field. It must be relative to
            the :ref:`startdir<buildconf-startdir>` or an absolute path.
            By default it's '.', that is, it's equal to
            :ref:`startdir<buildconf-startdir>`.

    There is simplified form of patterns using: if string value contains
    '*' or '?' it will be converted into ``dict`` form to use patterns.
    See examples below.

    Any path or pattern should be relative to the :ref:`startdir<buildconf-startdir>`.
    But for pattern (in dict) can be used custom ``startdir`` parameter.

    If paths contain spaces and all these paths are listed
    in one string then each such a path must be in quotes.

    Examples in python format:

    .. code-block:: python

        # just one file
        'source' : 'test.cpp'

        # list of two files
        'source' : 'main.c about.c'
        'source' : ['main.c', 'about.c'] # the same result

        # get all *.cpp files in the 'startdir' recursively
        'source' :  dict( include = '**/*.cpp' )
        # or
        'source' :  { 'include': '**/*.cpp' }
        # or
        'source' :  '**/*.cpp'

        # get all *.c and *.cpp files in the 'startdir' recursively
        'source' :  { 'include': ['**/*.c', '**/*.cpp'] }
        # or
        'source' :  ['**/*.c', '**/*.cpp']

        # get all *.cpp files in the 'startdir'/mylib recursively
        'source' :  dict( include = 'mylib/**/*.cpp' )

        # get all *.cpp files in the 'startdir'/src recursively
        # but don't include files according pattern 'src/extra*
        'source' :  dict( include = 'src/**/*.cpp', exclude = 'src/extra*' ),

    Examples in YAML format:

    .. code-block:: yaml

        # list of two files
        source : main.c about.c
        # or
        source : [main.c, about.c]

        # get all *.cpp files in the 'startdir'/mylib recursively
        source: { include: 'mylib/**/*.cpp' }
        # or
        source:
            include: 'mylib/**/*.cpp'

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-includes:

includes
"""""""""""""""""""""
    Include paths are used by the C/C++/D/Fortran compilers for finding headers/files.
    Paths should be relative to :ref:`startdir<buildconf-startdir>` or absolute.
    But last variant is not recommended.

    If paths contain spaces and all these paths are listed
    in one string then each such a path must be in quotes.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

export-includes
"""""""""""""""""""""
    If it's True then it exports value of ``includes`` for all build tasks
    which depend on the current task. Also it can be one or more paths
    for explicit exporting. By default it's False.

    If paths contain spaces and all these paths are listed
    in one string then each such a path must be in quotes.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-toolchain:

toolchain
"""""""""""""""""""""
    Name of toolchain/compiler to use in the task. It can be any system
    compiler that is supported by ZenMake or a toolchain from custom
    :ref:`toolchains<buildconf-toolchains>`.
    There are also the special names for autodetecting in format
    ``auto-*`` where ``*`` is a 'lang' feature for programming language,
    for example ``auto-c``, ``auto-c++``, etc.

    | Known names for C: ``auto-c``, ``gcc``, ``clang``, ``msvc``,
                            ``icc``, ``xlc``, ``suncc``, ``irixcc``.
    | Known names for C++: ``auto-c++``, ``g++``, ``clang++``, ``msvc``,
                            ``icpc``, ``xlc++``, ``sunc++``.
    | Known names for D: ``auto-d``, ``ldc2``, ``gdc``, ``dmd``.
    | Known names for Fortran: ``auto-fc``, ``gfortran``, ``ifort``.
    | Known names for Assembler: ``auto-asm``, ``gas``, ``nasm``.

    .. note::

        If you don't set ``toolchain`` then ZenMake will try to
        set ``auto-*`` itself
        according values in `features <buildconf-taskparams-features_>`_.

    ..
        But feature with autodetecting of language by file extensions cannot
        be used for autodetecting of correct ``auto-*``. For example, with
        ``cxxshlib`` ZenMake can set ``auto-c++`` itself but not
        with ``shlib``.

    In some rare cases this parameter can contain more than one value as a
    string with values separated by space or as list. For example, for case
    when C and Assembler files are used in one task, it can be ``"gcc gas"``.

    If toolchain from custom :ref:`toolchains<buildconf-toolchains>` or some
    system toolchain contain spaces in their names and all these toolchains are
    listed in one string then each
    such a toolchain must be in quotes.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

cflags
"""""""""""""""""""""
    One or more compiler flags for C.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

cxxflags
"""""""""""""""""""""
    One or more compiler flags for C++.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

dflags
"""""""""""""""""""""
    One or more compiler flags for D.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

fcflags
"""""""""""""""""""""
    One or more compiler flags for Fortran.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

asflags
"""""""""""""""""""""
    One or more compiler flags for Assembler.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

cppflags
"""""""""""""""""""""
    One or more compiler flags added at the end of compilation commands for C/C++.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

linkflags
"""""""""""""""""""""
    One or more linker flags for C/C++/D/Fortran.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

ldflags
"""""""""""""""""""""
    One or more linker flags for C/C++/D/Fortran at the end of the link command.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

aslinkflags
"""""""""""""""""""""
    One or more linker flags for Assembler.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

arflags
"""""""""""""""""""""
    Flags to give the archive-maintaining program.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

defines
"""""""""""""""""""""
    One or more defines for C/C++/Assembler/Fortran.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

export-defines
"""""""""""""""""""""
    If it's True then it exports value of ``defines`` for all build tasks
    which depend on the current task. Also it can be one or more defines
    for explicit exporting. By default it's False.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-use:

use
"""""""""""""""""""""
    This attribute enables the link against libraries (static or shared).
    It can be used for local libraries from other tasks or to declare
    dependencies between build tasks. Also it can be used to declare using of
    :ref:`external dependencies<dependencies-external>`.
    For external dependencies the format of any dependency in ``use`` must be:
    ``dependency-name:target-reference-name``.

    It can contain one or more the other task names.

    If a task name contain spaces and all these names are listed in one
    string then each such a name must be in quotes.

    Examples:

    .. code-block:: python

        'use' : 'util'
        'use' : 'util mylib'
        'use' : ['util', 'mylib']
        'use' : 'util "my lib"'
        'use' : ['util', 'my lib']
        'use' : 'util mylib someproject:somelib'

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

install-path
"""""""""""""""""""""
    String representing the installation path for the output files.
    It's used in commands ``install`` and ``uninstall``.
    To disable installation, set it to False or empty string.
    If it's absent then general values of ``${PREFIX}``, ``${BINDIR}``
    and ``${LIBDIR}`` will be used to detect path.
    You can use variables ``${PREFIX}``, ``${BINDIR}``, ``${LIBDIR}`` here
    like this:

    .. code-block:: python

        'install-path' : '${PREFIX}/exe'

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-libs:

libs
"""""""""""""""""""""
    One or more names of existing shared libraries as dependencies,
    without prefix or extension. Usually it's used to set system libraries.

    If you use this parameter to specify non-system shared libraries for some
    task you may need to specify the same libraries for all other tasks which
    depend on the current task. For example, you set library 'mylib'
    to the task A but the task B has parameter ``use`` with 'A',
    then it's recommended to add 'mylib' to the parameter ``libs`` of the
    task B. Otherwise you can get link error ``... undefined reference to ...``
    or something like that.
    Some other ways to solve this problem includes using environment variable
    ``LD_LIBRARY_PATH`` or changing of /etc/ld.so.conf file. But last way usually
    is not recommended.

    Example:

    .. code-block:: python

        'libs' : 'm rt'

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-libpath:

libpath
"""""""""""""""""""""
    One or more additional paths to find libraries. Usually you don't need to
    set it.

    If paths contain spaces and all these paths are listed
    in one string then each such a path must be in quotes.

    Example:

    .. code-block:: python

        'libpath' : '/local/lib'
        'libpath' : '/local/lib "my path"'

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

monitlibs
"""""""""""""""""""""
    One or more names from ``libs`` to monitor changes.

    For example, a project has used some system library 'superlib' and once this
    library was upgraded by a system package manager. After that the building of
    the project will not make a relink with the new version of 'superlib'
    if no changes in the project which can trigger such a relink.
    Usually it is not a problem because a project is changed much more frequently than
    upgrading of system libraries during development.

    Any names not from ``libs`` are ignored.

    It can be True or False as well. If it is True then value of ``libs``
    is used. If it is False then it means an empty list.

    By default it's False.

    Using of this parameter can slow down a building of some
    projects with a lot of values in this parameter.
    ZenMake uses sha1/md5 hashes to check changes of every library file.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

stlibs
"""""""""""""""""""""
    The same as ``libs`` but for static libraries.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

stlibpath
"""""""""""""""""""""
    The same as ``libpath`` but for static libraries.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

monitstlibs
"""""""""""""""""""""
    The same as ``monitlibs`` but for static libraries. It means it's affected
    by parameter ``stlibs``.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

rpath
"""""""""""""""""""""
    One or more paths to hard-code into the binary during
    linking time. It's ignored on platforms that do not support it.

    If paths contain spaces and all these paths are listed
    in one string then each such a path must be in quotes.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

ver-num
"""""""""""""""""""""
    Enforce version numbering on shared libraries. It can be used with
    \*shlib ``features`` for example. It can be ignored on platforms that do
    not support it.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-run:

run
"""""""""""""""""""""
    A :ref:`dict<buildconf-dict-def>` with parameters to run something in
    the task. It' used with task features ``runcmd`` and ``test``. It can be
    also just a string or a python function (for buildconf.py only). In this case
    it's the same as using dict with one parameter ``cmd``.

    :cmd:
        Command line to run. It can be any suitable command line.
        For convenience special variable ``TARGET`` can be
        used here. This variable contains the absolute path to resulting
        target file of the current task. There are also two additional
        provided by Waf variables that can be used: ``SRC`` and ``TGT``.
        They represent the task input and output Waf nodes
        (see description of node objects
        here: https://waf.io/book/#_node_objects).
        For python variant of buildconf it can be python function as well.
        It this case such a function gets one argument as a python dict
        with parameters:

        :taskname:
            Name of current build task
        :startdir:
            Current :ref:`startdir<buildconf-startdir>`
        :buildroot:
            Root directory for building
        :buildtype:
            Current buildtype
        :target:
            Absolute path to resulting target. It may not be existing.
        :waftask:
            Object of Waf class Task. It's for advanced use.

    :cwd:
        Working directory where to run ``cmd``. By default it's build
        directory for current buildtype. Path can be absolute or
        relative to the :ref:`startdir<buildconf-startdir>`.
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
            'run' : "echo 'say hello'",
        },

        'test.py' : {
            'run'      : {
                'cmd'   : 'python tests/test.py',
                'cwd'   : '.',
                'env'   : { 'JUST_ENV_VAR' : 'qwerty', },
                'shell' : False,
            },
            'config-actions'  : [ dict(do = 'check-programs', names = 'python'), ]
        },

        'shlib-test' : {
            'features' : 'cxxprogram test',
            # ...
            'run'      : {
                'cmd'     : '${TARGET} a b c',
                'env'     : { 'ENV_VAR1' : '111', 'ENV_VAR2' : 'false'},
                'repeat'  : 2,
                'timeout' : 10, # in seconds, Python 3 only
                'shell'   : False,
            },
        },

        'foo.luac' : {
            'source' : 'foo.lua',
            'config-actions' : [ dict(do = 'check-programs', names = 'luac'), ],
            'run': '${LUAC} -s -o ${TGT} ${SRC}',
        },

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-config-actions:

config-actions
"""""""""""""""""""""
    A list of configuration actions (configuration checks and others).
    Details are :ref:`here<config-actions>`.
    These actions are called on **configure** step (command **configure**).

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-export-config-actions:

export-config-actions
"""""""""""""""""""""
    If it's True then it exports all results of
    :ref:`config-actions<buildconf-taskparams-config-actions>` for all
    build tasks which depend on the current task.
    By default it's False.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

normalize-target-name
"""""""""""""""""""""
    Convert ``target`` name to ensure the name is suitable for file name
    and has not any potential problems.
    It replaces all space symbols for example. Experimental.
    By default it is False.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

objfile-index
"""""""""""""""""""""
    Counter for the object file extension.
    By default it's calculated automatically as unique index number for each
    build task.

    If you set this for one task but not for others in the same project and your
    selected index number is matched with an one of automatic generated indexes
    then it can cause compilation errors if different tasks uses the same files in
    parameter ``source``.

    Also you can set the same value for the all build tasks and often it's not a
    problem while different tasks uses the different files in
    parameter ``source``.

    Set this parameter only if you know what you do.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. note::

    More examples of buildconf files can be found in repository
    `here <repo_demo_projects_>`_.