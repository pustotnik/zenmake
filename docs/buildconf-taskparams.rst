.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-taskparams:

Build config: task parameters
=============================

It's a :ref:`dict<buildconf-dict-def>` as a collection of build task parameters
for a build task. This collection is used in :ref:`tasks<buildconf-tasks>`,
:ref:`buildtypes<buildconf-buildtypes>` and :ref:`byfilter<buildconf-byfilter>`.
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

    Examples in YAML format:

    .. code-block:: yaml

        features : cprogram
        features : cxxshlib
        features : cxxprogram runcmd
        features : cxxprogram test

    Examples in Python format:

    .. code-block:: python

        'features' : 'cprogram'
        'features' : 'cxxshlib'
        'features' : 'cxxprogram runcmd'
        'features' : 'cxxprogram test'

.. _buildconf-taskparams-target:

target
"""""""""""""""""""""
    Name of resulting file. The target will have different extension and
    name depending on the platform but you don't need to declare this
    difference explicitly. It will be generated automatically. For example
    the ``sample`` for \*shlib task will be converted into
    ``sample.dll`` on Windows and into ``libsample.so`` on Linux.
    By default it's equal to the name of the build task. So in most cases
    it is not needed to be set explicitly.

    You can use :ref:`substitution<buildconf-substitutions>`
    variables for this parameter.

    And it's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-source:

source
"""""""""""""""""""""
    One or more source files for compiler/toolchain.
    It can be:

        - a string with one or more paths separated by space
        - a :ref:`dict<buildconf-dict-def>`, description see below
        - a list of items where each item is a string with one or more paths or a dict

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

        :incl:
            Ant pattern or list of patterns to include, required field.
        :excl:
            Ant pattern or list of patterns to exclude, optional field.
        :ignorecase:
            Ignore case while matching (False by default), optional field.
        :startdir:
            Start directory for patterns, optional field. It must be relative to
            the :ref:`startdir<buildconf-startdir>` or an absolute path.
            By default it's '.', that is, it's equal to
            :ref:`startdir<buildconf-startdir>`.

    ZenMake always adds several patterns to exclude files for any ant pattern.
    These patterns include `Default Excludes` from
    `Ant patterns <https://ant.apache.org/manual/dirtasks.html>`_ and some additional
    patterns like ``**/*.swp``.

    There is simplified form of ant patterns using: if string value contains
    '*' or '?' it will be converted into ``dict`` form to use patterns.
    See examples below.

    Any path or pattern should be relative to the :ref:`startdir<buildconf-startdir>`.
    But for pattern (in dict) can be used custom ``startdir`` parameter.

    .. note::

        If paths contain spaces and all these paths are listed
        in one string then each such a path must be in quotes.

        *YAML*: You can write a string without quotes (as a plain scalar) in many
        cases but there are some special symbols which can not be used at the
        beginning without quotes, for example ``*`` and ``?<space>``.
        So a value like ``**/*.cpp`` must be always in qoutes (``'`` or ``"``).

        See details here: https://www.yaml.info/learn/quote.html.

    Examples in YAML format:

    .. code-block:: yaml

        # just one file
        source : test.cpp

        # list of two files
        source : main.c about.c
        # or
        source : [main.c, about.c]

        # get all *.cpp files in the 'startdir' recursively
        source : { incl: '**/*.cpp' }
        # or
        source :
            incl: '**/*.cpp'
        # or (shortest record with the same result)
        source : '**/*.cpp'

        # get all *.c and *.cpp files in the 'startdir' recursively
        source :  { incl: '**/*.c **/*.cpp' }
        # or (shorter record with the same result)
        source : '**/*.c **/*.cpp'

        # get all *.cpp files in the 'startdir'/mylib recursively
        source :  mylib/**/*.cpp

        # get all *.cpp files in the 'startdir'/src recursively
        # but don't include files according pattern 'src/extra*'
        source :
            incl: src/**/*.cpp
            excl: src/extra*

        # get all *.c files in the 'src' and in '../others' recursively
        source :
            - 'src/**/*.c'
            - incl: '**/*.c'
              startdir: ../others

        # pattern with space, it's necessary to use both types of quotes here:
        source : '"my prog/**/*.c"'

        # two file paths with spaces
        source : '"my shlib/my util.c" "my shlib/my util2.c"'

    Examples in python format:

    .. code-block:: python

        # just one file
        'source' : 'test.cpp'

        # list of two files
        'source' : 'main.c about.c'
        'source' : ['main.c', 'about.c'] # the same result

        # get all *.cpp files in the 'startdir' recursively
        'source' :  dict( incl = '**/*.cpp' )
        # or
        'source' :  { 'incl': '**/*.cpp' }
        # or (shortest record with the same result)
        'source' :  '**/*.cpp'

        # get all *.c and *.cpp files in the 'startdir' recursively
        'source' :  { 'incl': ['**/*.c', '**/*.cpp'] }
        # or (shorter record with the same result)
        'source' :  ['**/*.c', '**/*.cpp']

        # get all *.cpp files in the 'startdir'/mylib recursively
        'source' :  'mylib/**/*.cpp'

        # get all *.cpp files in the 'startdir'/src recursively
        # but don't include files according pattern 'src/extra*'
        'source' :  dict( incl = 'src/**/*.cpp', excl = 'src/extra*' )

        # get all *.c files in the 'src' and in '../others' recursively
        'source'   : [
            'src/**/*.c',
            { 'incl': '**/*.c', 'startdir' : '../others' },
        ]

        # pattern with space:
        'source' : '"my prog/**/*.c"'

        # two file paths with spaces
        'source' : '"my shlib/my util.c" "my shlib/my util2.c"'

    You can use :ref:`substitution<buildconf-substitutions>`
    variables in string values for this parameter.

    And it's possible to use :ref:`selectable parameters<buildconf-select>`
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

    This parameter can be :ref:`exported<buildconf-taskparams-export>`.

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

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

cxxflags
"""""""""""""""""""""
    One or more compiler flags for C++.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

dflags
"""""""""""""""""""""
    One or more compiler flags for D.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

fcflags
"""""""""""""""""""""
    One or more compiler flags for Fortran.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

asflags
"""""""""""""""""""""
    One or more compiler flags for Assembler.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

cppflags
"""""""""""""""""""""
    One or more compiler flags added at the end of compilation commands for C/C++.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

linkflags
"""""""""""""""""""""
    One or more linker flags for C/C++/D/Fortran.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

ldflags
"""""""""""""""""""""
    One or more linker flags for C/C++/D/Fortran at the end of the link command.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

aslinkflags
"""""""""""""""""""""
    One or more linker flags for Assembler.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

arflags
"""""""""""""""""""""
    Flags to give the archive-maintaining program.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

.. _buildconf-taskparams-defines:

defines
"""""""""""""""""""""
    One or more defines for C/C++/Assembler/Fortran.

    Examples in YAML format:

    .. code-block:: yaml

        defines : MYDEFINE

        defines : [ ABC=1, DOIT ]

        defines :
            - ABC=1
            - DOIT

        defines : 'ABC=1 DOIT AAA="some long string"'

    Examples in Python format:

    .. code-block:: python

        'defines' : 'MYDEFINE'

        'defines' : ['ABC=1', 'DOIT']

        'defines' : 'ABC=1 DOIT AAA="some long string"'

    You can use :ref:`substitution<buildconf-substitutions>`
    variables for this parameter.

    And it's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

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

    Examples in YAML format:

    .. code-block:: yaml

        use : util
        use : util mylib
        use : [util, mylib]
        use : 'util "my lib"'
        use : ['util', 'my lib']
        use : util mylib someproject:somelib

    Examples in Python format:

    .. code-block:: python

        'use' : 'util'
        'use' : 'util mylib'
        'use' : ['util', 'mylib']
        'use' : 'util "my lib"'
        'use' : ['util', 'my lib']
        'use' : 'util mylib someproject:somelib'

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
    then it's recommended to add 'mylib' to the parameter ``libs`` for the
    task B. Otherwise you can get link error ``... undefined reference to ...``
    or something like that.
    Some other ways to solve this problem include using environment variable
    ``LD_LIBRARY_PATH`` or changing of /etc/ld.so.conf file. But usually last
    method is not recommended.

    Example in YAML format:

    .. code-block:: yaml

        libs : m rt

    Example in Python format:

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

    Paths should be absolute or relative to :ref:`startdir<buildconf-startdir>`.

    Examples in YAML format:

    .. code-block:: yaml

        libpath : /local/lib
        libpath : '/local/lib "my path"' # in case of spaces in a path

    Examples in Python format:

    .. code-block:: python

        'libpath' : '/local/lib'
        'libpath' : '/local/lib "my path"' # in case of spaces in a path

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

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

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

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

.. _buildconf-taskparams-ver-num:

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
        For convenience special :ref:`substitution<buildconf-substitutions>`
        variable ``TARGET`` can be
        used here. This variable contains the absolute path to resulting
        target file of the current task. There are also two additional
        provided by Waf substitution variables that can be used: ``SRC`` and ``TGT``.
        They represent the task input and output Waf nodes
        (see description of node objects
        here: https://waf.io/book/#_node_objects).
        Actually ``SRC`` and ``TGT`` are not real variables and they cannot be
        changed in a buildconf file.

        Environment variables also can be used here but you cannot use syntax
        with curly braces because this syntax is used for internal substitutions.

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

    If current task has parameter ``run`` with empty ``features`` or with only ``runcmd``
    in the ``features`` then it is standalone runcmd task.

    If current task is not standalone runcmd task then command from parameter
    ``run`` will be run after compilation and linking. If you want to have
    a command that will be called before compilation and linking you can make
    another standalone runcmd task and specify this new task in the parameter
    ``use`` of the current task.

    By default ZenMake expects that any build task produces a target file
    and if it doesn't find this file when the task is finished
    it will throw an error. And it is true for standalone runcmd tasks also.
    If you want to create standalone runcmd task which doesn't produce target
    file you can set task parameter
    :ref:`target<buildconf-taskparams-target>` to an empty string.

    Examples in YAML format:

    .. code-block:: yaml

        echo:
            run: "echo 'say hello'"
            target: ''

        test.py:
            run:
                cmd   : python tests/test.py
                cwd   : .
                env   : { JUST_ENV_VAR: qwerty }
                shell : false
            target: ''
            configure :
                - do: find-program
                  names: python

        shlib-test:
            features : cxxprogram test
            # ...
            run:
                cmd     : '${TARGET} a b c'
                env     : { ENV_VAR1: '111', ENV_VAR2: 'false' }
                repeat  : 2
                timeout : 10 # in seconds
                shell   : false

        foo.luac:
            source : foo.lua
            configure : [ { do: find-program, names: luac } ]
            run: '${LUAC} -s -o ${TGT} ${SRC}'

    Examples in Python format:

    .. code-block:: python

        'echo' : {
            'run' : "echo 'say hello'",
            'target': '',
        },

        'test.py' : {
            'run'      : {
                'cmd'   : 'python tests/test.py',
                'cwd'   : '.',
                'env'   : { 'JUST_ENV_VAR' : 'qwerty', },
                'shell' : False,
            },
            'target': '',
            'configure'  : [ dict(do = 'find-program', names = 'python'), ]
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
            'configure' : [ dict(do = 'find-program', names = 'luac'), ],
            'run': '${LUAC} -s -o ${TGT} ${SRC}',
        },

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. _buildconf-taskparams-configure:

configure
"""""""""""""""""""""
    A list of configuration actions (configuration checks and others).
    Details are :ref:`here<config-actions>`.
    These actions are called on **configure** step (in command **configure**).

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Results of these configuration actions
    can be :ref:`exported<buildconf-taskparams-export>` with the name `config-results`.

.. _buildconf-taskparams-substvars:

substvars
"""""""""""""""""""""
    A :ref:`dict<buildconf-dict-def>` with substitution variables which can be
    used, for example, in :ref:`parameter 'run'<buildconf-taskparams-run>`.

    Current variables are visible in current task only.

    See details :ref:`here<buildconf-substitutions>`.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

    Also this parameter can be :ref:`exported<buildconf-taskparams-export>`.

.. _buildconf-taskparams-export:

export-<param> / export
""""""""""""""""""""""""

    Some task parameters can be exported to all dependent build tasks.

    There two forms: ``export-<param>`` and ``export``.

    In first form ``<param>`` is a name of task parameter that can be exported.
    As value can be used True/False or specific value to export.
    If value is True then ZenMake exports value of parameter from current task
    to all dependent build tasks. If value is False then ZenMake
    exports nothing.

    Supported names:  ``includes``, ``defines``, ``config-results``,
    ``libpath``, ``stlibpath``, ``substvars`` and all ``*flags``.

    The parameter with ``config-results`` can not be used to export specific values.
    It always must be True/False only.

    In second form it must be string or list with the names of parameters to export.
    Second form is simplified form of the first form when all values are True.
    This form can not be used to set specific value to export.

    By default ZenMake doesn't export anything (all values are False).

    Exported values are inserted in the beginning of the current parameter values
    in dependent tasks. It was made to have ability to overwrite parent values.
    For example, task A has ``defines`` with value ``AAA=q`` and task B depends
    on task A and has ``defines`` with value ``BBB=v``. So if task A has
    ``export-defines`` with True, then actual value of ``defines`` in task B will
    be ``AAA=q BBB=v``.

    Examples in YAML format:

    .. code-block:: yaml

        # export all includes from current task
        export-includes: true
        # the same result:
        export: includes

        # export all includes and defines from current task
        export-includes: true
        export-defines: true
        # the same result:
        export: includes defines

        # export specific includes, value of parameter 'includes' from current
        # task is not used
        export-includes: incl1 incl2

        # export specific defines, value of parameter 'defines' from current
        # task is not used
        export-defines  : 'ABC=1 DOIT AAA="some long string"'

        # export results of all configuration actions from current task
        export-config-results: true

        # export all includes, defines and results of configuration actions
        export: includes defines config-results

    Specific remarks:

        :includes:
            If specified paths contain spaces and all these paths are listed
            in one string then each such a path must be in quotes.

        :defines:
            Defines from :ref:`configuration actions<config-actions>`
            are not exported. Use ``export-config-results`` or
            ``export`` with ``config-results`` for that.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

install-path
"""""""""""""""""""""
    String representing the installation path for the output files.
    It's used in commands ``install`` and ``uninstall``.
    To disable installation, set it to False or empty string.
    If it's absent then general values of ``PREFIX``, ``BINDIR``
    and ``LIBDIR`` will be used to detect path.
    Path must be absolute.
    You can use any :ref:`substitution<buildconf-substitutions>` variable
    including ``${PREFIX}``, ``${BINDIR}`` and ``${LIBDIR}`` here
    like this:

    Example in YAML format:

    .. code-block:: yaml

        install-path : '${PREFIX}/exe'

    By default this parameter is false for standalone runcmd tasks.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

install-files
"""""""""""""""""""""
    A list of additional files to install.
    Each item in this list must be a :ref:`dict<buildconf-dict-def>` with
    following parameters:

    :do:
        It is what to do and can be ``copy``, ``copy-as`` or ``symlink``.
        Value ``copy`` means copying specified files to a directory from ``dst``.
        Value ``copy-as`` means copying one specified file to a path from ``dst``
        so you use a difference file name.
        Value ``symlink`` means creation of symlink. It's for POSIX platforms only
        and do nothing on MS Windows.

        You may not set this parameter in some cases.
        If this parameter is absent:

        - It's ``symlink`` if parameter ``symlink`` exists in current dict.
        - It's ``copy`` in other cases.
    :src:
        If ``do`` is ``copy`` then rules for this parameter the same as for
        `source <buildconf-taskparams-source_>`_ but with one addition: you can
        specify one or more paths to directory if you don't use any ant pattern.
        In this case all files from specified directory will be copied
        recursively with directories hierarchy.

        If ``do`` is ``copy-as``, it must one path to a file. It must be relative
        to the :ref:`startdir<buildconf-startdir>` or an absolute path.

        If ``do`` is ``symlink``, it must one path to a file. Created symbolic
        link will point to this path. It must be relative
        to the :ref:`startdir<buildconf-startdir>` or an absolute path.

        You can use any :ref:`substitution<buildconf-substitutions>` variable
        here.
    :dst:
        If ``do`` is ``copy`` then it must be path to a directory.
        If ``do`` is ``copy-as``, it must one path to a file.
        If ``do`` is ``symlink``, this parameter cannot be used. See parameter ``symlink``.

        It must be relative to the :ref:`startdir<buildconf-startdir>` or
        an absolute path.

        You can use any :ref:`substitution<buildconf-substitutions>` variable
        here.

        Any path here will have value of ``destdir``
        at the beginning if this ``destdir`` is set to non-empty value.
        This ``destdir`` can be set from command line argument ``--destdir`` or from
        environment variable ``DESTDIR`` and it is not set by default.

    :symlink:
        It is like ``dst`` for ``copy-as`` but for creating a symlink.
        This parameter can be used only if ``do`` is ``symlink``.

        It must be relative to the :ref:`startdir<buildconf-startdir>` or
        an absolute path.

        You can use any :ref:`substitution<buildconf-substitutions>` variable
        here.

    :chmod:
        Change file mode bits. It's for POSIX platforms only
        and do nothing on MS Windows.
        And it can not be used for ``do`` = ``symlink``.

        It must be integer or string. If it is integer it must be correct value
        for python function os.chmod. For example: 0o755.

        If it is string then value will be converted to integer as octal
        representation of an integer.
        For example, '755' will be converted to 493 (it's 755 in octal representation).

        By default it is 0o644.

    :user:
        Change file owner. It's for POSIX platforms only
        and do nothing on MS Windows.
        It must be name of existing user.
        It is not set by default and value from original file will be used.

    :group:
        Change file user's group. It's for POSIX platforms only
        and do nothing on MS Windows.
        It must be name of existing user's group.
        It is not set by default and value from original file will be used.

    :follow-symlinks:
        Follow symlinks from ``src`` if ``do`` is ``copy`` or ``copy-as``.
        If it is false, symbolic links in the paths from ``src`` are
        represented as symbolic links in the ``dst``, but the metadata of the
        original links is NOT copied; if true or omitted, the contents and
        metadata of the linked files are copied to the new destination.

        It's true by default.

    :relative:
        This parameter can be used only if ``do`` is ``symlink``.
        If it is true, relative symlink will created.

        It's false by default.

    Some examples can be found in the directory 'mixed/01-cshlib-cxxprogram'
    in the repository `here <repo_demo_projects_>`_.

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

enabled
"""""""""""""""""""""
    If it's False then current task will not be used at all.
    By default it is True.

    It has sense mostly to use with
    :ref:`selectable parameters<buildconf-select>` or with
    :ref:`byfilter<buildconf-byfilter>`. With this parameter you can make a build
    task which can be used, for example, on Linux only or for specific toolchain
    or with another condition.

group-dependent-tasks
"""""""""""""""""""""
    Although runtime jobs for the tasks may be executed in parallel, some
    preparation is made before this in one thread. It includes, for example,
    analyzing of the task dependencies and file paths in :ref:`source<buildconf-taskparams-source>`.
    Such list of tasks is called `build group` and, by default, it's only one
    build group for each project which uses ZenMake. If this parameter is true,
    ZenMake creates a new build group for all other dependent tasks and
    preparation for these dependent tasks will be run only when all jobs for current
    task, including all dependencies, are done.

    For example, if some task produces source files (\*.c, \*.cpp, etc) that
    don't exist at the time
    of such a preparation, you can get a problem because ZenMake cannot find
    not existing files. It is not a problem if such a
    file is declared in :ref:`target<buildconf-taskparams-target>` and then this
    file is specified without use of ant pattern in ``source`` of dependent tasks.
    In other cases you can solve the problem by setting this parameter to True
    for a task which produces these source files.

    By default it is False. Don't set it to True without reasons because it
    can slow building down.

objfile-index
"""""""""""""""""""""
    Counter for the object file extension.
    By default it's calculated automatically as unique index number for each
    build task.

    If you set this for one task but not for others in the same project and your
    index number is matched with one of automatic generated indexes
    then it can cause compilation errors if different tasks use the same files in
    parameter ``source``.

    Also you can set the same value for the all build tasks and often it's not a
    problem while different tasks use the different files in
    parameter ``source``.

    Set this parameter only if you know what you do.

    It's possible to use :ref:`selectable parameters<buildconf-select>`
    to set this parameter.

.. note::

    More examples of buildconf files can be found in repository
    `here <repo_demo_projects_>`_.