.. include:: global.rst.inc
.. highlight:: python
.. _buildconf-select:

Build config: selectable parameters
===================================

ZenMake provides ability to select values for parameters in
:ref:`task params<buildconf-taskparams>` depending on some conditions.
This feature of ZenMake is similar to `Configurable attributes` from
Bazel build system and main idea was borrowed from that system. But
implementation is different.

It can be used for selecting different source files, includes, compiler flags
and others on different platforms, different toolchains, etc.

Example in YAML format:

.. code-block:: yaml

    tasks:
        # ...

    conditions:
        windows-msvc:
            platform: windows
            toolchain: msvc

    buildtypes:
        debug: {}
        release:
            cxxflags.select:
                windows-msvc: /O2
                default: -O2

Example in Python format:

.. code-block:: python

    tasks = {
        # ...
    }

    conditions = {
        'windows-msvc' : {
            'platform' : 'windows',
            'toolchain' : 'msvc',
        },
    }

    buildtypes = {
        'debug' : {
        },
        'release' : {
            'cxxflags.select' : {
                'windows-msvc': '/O2',
                'default': '-O2',
            },
        },
    }

In this example for build type 'release' we set value '/O2' to 'cxxflags'
if toolchain 'msvc' is used on MS Windows and set '-02' for all other cases.

This method can be used for any parameter in :ref:`task params<buildconf-taskparams>`
excluding :ref:`features<buildconf-taskparams-features>` in the form:

YAML format:

.. code-block:: yaml

    <parameter name>.select:
        <condition name1>: <value>
        <condition name2>: <value>
        ...
        default: <value>

Python format:

.. code-block:: python

    '<parameter name>.select' : {
        '<condition name1>' : <value>,
        '<condition name2>' : <value>,
        ...
        'default' : <value>,
    }

A <parameter name> here is a parameter from :ref:`task params<buildconf-taskparams>`.
Examples: 'toolchain.select', 'source.select', 'use.select', etc.

Each condition name must refer to a key in :ref:`conditions<buildconf-conditions>`
or to one of built-in conditions (see below).
There is also special optional key ``default`` wich means default value if none
of the conditions has been selected. If the key ``default`` doen't exist then ZenMake
tries to use the value of <parameter name> if it exists. If none of the
conditions has been selected and no default value for the parameter then this
parameter will not be used.

Keys in :ref:`conditions<buildconf-conditions>` are just strings with any
characters excluding white spaces. A value of each condition is a dict with
one or more such parameters:

    :platform:
        Selected platform like 'linux', 'windows', 'darwin', etc.
        Valid values are the same as for ``default`` in
        the :ref:`buildtypes<buildconf-buildtypes>`.

        It can be one value or list of values or string with more than one
        value separated by spaces like this: 'linux windows'.

    :cpu-arch:
        Selected current CPU architecture. Actual it's a result of the python function
        platform.machine() See https://docs.python.org/library/platform.html.
        Some possible values are: arm, i386, i686, x86_64, AMD64.
        Real value depends also on platform. For example, on Windows you can get
        AMD64 while on Linux you gets x86_64 on the same host.

        Current value can be obtained also with the command ``zenmake sysinfo``.

        It can be one value or list of values or string with more than one value
        separated by spaces like this: 'i686 x86_64'.

    :toolchain:
        Selected/detected toolchain.

        It can be one value or list of values or string with more than one value
        separated by spaces like this: 'gcc clang'.

    :task:
        Selected build task name.

        It can be one value or list of values or string with more than one value
        separated by spaces like this: 'mylib myprogram'.

    :buildtype:
        Selected buildtype.

        It can be one value or list of values or string with more than one value
        separated by spaces like this: 'debug release'.

    :env:
        Check system environment variables. It's a dict of pairs <variable> : <value>.

        Example in YAML format:

        .. code-block:: yaml

            conditions:
                my-env:
                    env:
                        TEST: 'true' # use 'true' as a string
                        CXX: gcc

        Example in Python format:

        .. code-block:: python

           conditions = {
                'my-env' : {
                    'env' : {
                        'TEST' : 'true',
                        'CXX' : 'gcc',
                    }
                },
            }

If a parameter in a condition contains more than one value then any of these
values will fulfill selected condition. It means if some condition, for example,
has ``platform`` which contains ``'linux windows'`` without other parameters then
this condition will be selected on any of these platforms (on GNU/Linux and
on MS Windows). But with parameter ``env`` the situation is different. This
parameter can contain more than one environment variable and a condition will be
selected only when all of these variables are equal to existing variables from the
system environment. If you want to have condition to select by any of such
variables you can do it by making different conditions in
:ref:`conditions<buildconf-conditions>`.

.. note::
    There is one limitation for ``toolchain.select`` - it's not possible to use
    condition with 'toolchain' parameter inside ``toolchain.select``.

Only one record from ``*.select`` for each parameter can be selected for each task
during configuring but condition name in ``*.select`` can be string with more than
one name from ``conditions``. Such names must be
just separated by spaces in the string. In this case it is considered like
(it's not real example):

.. code-block:: yaml

    <parameter name>.select:
        <name1 AND name2>: <value>
        ...

Example in YAML format:

.. code-block:: yaml

    conditions:
        linux:
            platform: linux
        g++:
            toolchain: g++

    buildtypes:
        debug: {}
        release:
            cxxflags.select:
                # will be selected only on linux with selected/detected toolchain g++
                linux g++: -Ofast
                # will be selected in all other cases
                default: -O2

Example in Python format:

.. code-block:: python

    conditions = {
        'linux' : {
            'platform' : 'linux',
        },
        'g++' : {
            'toolchain' : 'g++',
        },
    }

    buildtypes = {
        'debug' : {
        },
        'release' : {
            'cxxflags.select' : {
                # will be selected only on linux with selected/detected toolchain g++
                'linux g++': '-Ofast',
                # will be selected in all other cases
                'default': '-O2',
            },
        },
    }

For convenience there are ready to use built-in conditions for known platforms and
supported toolchains. So in example above the ``conditions`` variable is not needed
at all because conditions with names ``linux`` and ``g++`` already exist:

in YAML format:

.. code-block:: yaml

    # no declaration of conditions

    buildtypes:
        debug: {}
        release:
            cxxflags.select:
                # will be selected only on linux with selected/detected toolchain g++
                linux g++: -Ofast
                # will be selected in all other cases
                default: -O2

in Python format:

.. code-block:: python

    # no declaration of conditions

    buildtypes = {
        'debug' : {
        },
        'release' : {
            'cxxflags.select' : {
                # will be selected only on linux with selected/detected toolchain g++
                'linux g++': '-Ofast',
                # will be selected in all other cases
                'default': '-O2',
            },
        },
    }

Also you can use built-in conditions for supported buildtypes. But if any name
of supported buildtype is the same as one of known platforms or supported
toolchains then such a buildtype cannot be used as a built-in condition.
For example, you may want to make/use the buildtype 'linux' and it will be possible
but you have to declare a different name to use it in conditions in this case
because the 'linux' value is one of known platforms.

There is one detail about built-in conditions for toolchains - only toolchains
supported for current build tasks can be used. ZenMake detects them from
all ``features`` of all existing build tasks in current project during configuring.
For example, if tasks exist for C language only then supported toolchains for
all other languages cannot be used as a built-in condition.

If you declare condition in :ref:`conditions<buildconf-conditions>` with the
same name of a built-in condition then your condition will be used instead
of that built-in condition.
