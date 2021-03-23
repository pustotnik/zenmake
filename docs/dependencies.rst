.. include:: global.rst.inc
.. highlight:: console
.. _dependencies:

Dependencies
============

ZenMake supports several types of dependencies for build projects:

.. contents::
   :local:

System libraries
------------------------------
System libraries can be specified by using the config parameter
:ref:`libs<buildconf-taskparams-libs>`.
Usually you don't need to set paths to system libraries but you can set them
using the config parameter :ref:`libpath<buildconf-taskparams-libpath>`.

Local libraries
------------------------------
Local libraries are libraries from your project. Use the config parameter
:ref:`use<buildconf-taskparams-use>` to specify such dependencies.

.. _dependencies-subdirs:

Sub buildconfs
------------------------------
You can organize building of your project by using more than one
:ref:`buildconf<buildconf>` file in some sub directories of your project.
In this case ZenMake merges parameters from all such buildconf files.
But you must specify these sub directories by using the config parameter
:ref:`subdirs<buildconf-subdirs>`.

Parameters in the sub buildconf can always overwrite matching parameters
from the parent :ref:`buildconf<buildconf>`. But some parameters are not changed.

These parameters can be set only in the the top-level buildconf:

    ``buildroot``, ``realbuildroot``, ``project``, ``features``, ``cliopts``

Also default build type can be set only in the top-level buildconf.

These parameters are always used without merging with parent buildconfs:

    ``startdir``, ``subdirs``, ``tasks``

ZenMake doesn't merge your own variables in your buildconf
files if you use some of them.
Other variables are merged including ``byfilter``. But build tasks in
the ``byfilter`` which are not from the current buildconf are ignored
excepting explicit specified ones.

Some examples can be found in the directory 'subdirs'
in the repository `here <repo_demo_projects_>`_.

.. _dependencies-external:

External dependencies
------------------------------

A few basic types of external dependencies can be used:

    - :ref:`Depending on other ZenMake projects<dependencies-external-zenmake>`
    - :ref:`Depending on non-ZenMake projects<dependencies-external-non-zenmake>`

See full description of buildconf parameters for external dependencies
:ref:`here<buildconf-edep-params>`.

.. _dependencies-external-zenmake:

ZenMake projects
""""""""""""""""""""

Configuration for this type of dependency is simple in most cases: you set up
the config variable :ref:`edeps<buildconf-edeps>` with
the :ref:`rootdir<buildconf-edep-params-rootdir>` and
the :ref:`export-includes<buildconf-edep-params-export-includes>` (if it's necessary)
and then specify this dependency in :ref:`use<buildconf-taskparams-use>`, using existing
task names from dependency buildconf.

Example in Python format:

    .. code-block:: python

        edeps = {
            'zmdep' : {
                'rootdir': '../zmdep',
                'export-includes' : '../zmdep',
            },
        }

        tasks = {
            'myutil' : {
                'features' : 'cxxshlib',
                'source'   : 'shlib/**/*.cpp',
                # Names 'calclib' and 'printlib' are existing tasks in 'zmdep' project
                'use' : 'zmdep:calclib zmdep:printlib',
            },
        }

Additionally, in some cases, the parameter
:ref:`buildtypes-map<buildconf-edep-params-buildtypes-map>` can be useful.

Also it's recommended to use always the same version of ZenMake for all such projects.
Otherwise there are some compatible problems can be occured.

.. note::
    Command line options ``--force-edeps`` and ``--buildtype``
    for current project will affect rules for its external dependencies
    while all other command line options will be ignored.
    You can use :ref:`environment variables<envvars>`
    to have effect on all external dependencies. And, of course, you can set up
    each buildconf in the dependencies to have desirable behavior.

.. _dependencies-external-non-zenmake:

Non-ZenMake projects
"""""""""""""""""""""

You can use external dependencies from some other build systems but in this
case you need to set up more parameters in the config
variable :ref:`edeps<buildconf-edeps>`. Full description of these
parameters can be found :ref:`here<buildconf-edep-params>`. Only one parameter
``buildtypes-map`` is not used for such dependencies.

If it's necessary to set up different targets for different buildtypes you
can use :ref:`selectable parameters<buildconf-select>` in build tasks of your
ZenMake project.

Example in Python format:

    .. code-block:: python

        foolibdir = '../foo-lib'

        edeps = {
            'foo-lib-d' : {
                'rootdir': foolibdir,
                'export-includes' : foolibdir,
                'targets': {
                    'shared-lib' : {
                        'dir' : foolibdir + '/_build_/debug',
                        'type': 'shlib',
                        'name': 'fooutil',
                    },
                },
                'rules' : {
                    'build' : 'make debug',
                },
            },
            'foo-lib-r' : {
                'rootdir': foolibdir,
                'export-includes' : foolibdir,
                'targets': {
                    'shared-lib' : {
                        'dir' : foolibdir + '/_build_/release',
                        'type': 'shlib',
                        'name': 'fooutil',
                    },
                },
                'rules' : {
                    'build' : 'make release',
                },
            },
        }

        tasks = {
            'util' : {
                'features' : 'cxxshlib',
                'source'   : 'shlib/**/*.cpp',
            },
            'program' : {
                'features' : 'cxxprogram',
                'source'   : 'prog/**/*.cpp',
                'use.select' : {
                    'debug'   : 'util foo-lib-d:shared-lib',
                    'release' : 'util foo-lib-r:shared-lib',
                },
            },
        }

Common notes
"""""""""""""""""""""

You can use command line option ``-E``/``--force-edeps`` to run rules for
external dependencies without checking triggers.

Some examples can be found in the directory 'external-deps'
in the repository `here <repo_demo_projects_>`_.
