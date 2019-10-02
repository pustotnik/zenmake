.. include:: global.rst.inc
.. _buildconf:

Build config
============

ZenMake uses build configuration file with name ``buildconf.py`` or
``buildconf.yaml``. First variant is a regular python file and second is
a YAML file. ZenMake doesn't use both files at the same time. If both files
exist in the root of a project then only ``buildconf.py`` will be used.

Format for both config files are the same. YAML variant is a little more
readable but in python variant you can add custom python code if you wish.


tasks
    Build tasks. Each task has name and parameters.

buildtypes
    Build types like ``debug``, ``release`` and so on.
