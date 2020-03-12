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
System libraries can be specified using config parameter ``libs``.
Usually you don't need to set paths to system libraries but you can set them
using config parameter ``libpath``. More details about using of these
parameters you can find :ref:`here<buildconf-taskparams>`.

Local libraries
------------------------------
Local libraries are libraries from your project. Use config parameter ``use``
to specify such dependencies.
More details about using of these
parameters you can find :ref:`here<buildconf-taskparams>`.

Sub buildconfs
------------------------------
You can organize building of your project by using more than one
:ref:`buildconf<buildconf>` file in some sub directories of your project.
In this case ZenMake merges parameters from all such buildconf files.
But you must specify these sub directories by config parameter
:ref:`subdirs<buildconf-subdirs>`.

Parameters in the sub buildconf can always overwrite matching parameters
from the parent :ref:`buildconf<buildconf>`. But some parameters are not changed.

These parameters can be set only in the the top-level buildconf:

    ``options``, ``buildroot``, ``realbuildroot``

Also default build type can be set only in the top-level buildconf.

These parameters are always used without merging with the parent buildconfs:

    ``startdir``, ``subdirs``, ``tasks``

ZenMake doesn't merge your own variables in your buildconf
files if you use some of them.
Other variables are merged including ``matrix``. But build tasks in
the ``matrix`` which are not from the current buildconf are ignored
excepting explicit specified ones.

Some examples can be found in the directory 'subdirs'
in the repository `here <repo_demo_projects_>`_.