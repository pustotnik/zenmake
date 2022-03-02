.. include:: global.rst.inc
.. _toolkits:

Supported toolkits
===================

.. _toolkits_qt5:

Qt5
-----------

To build C++ project with Qt5 you can put ``qt5``
in :ref:`features<buildconf-taskparams-features>`.
In such tasks in the :ref:`source<buildconf-taskparams-source>` parameter
not only .cpp files but .qrc, .ui and .ts files can be specified as well.

There are additional task parameters for Qt5 tasks:
:ref:`moc<buildconf-taskparams-moc>`,
:ref:`rclangprefix<buildconf-taskparams-rclangprefix>`,
:ref:`langdir-defname<buildconf-taskparams-langdir-defname>`,
:ref:`bld-langprefix<buildconf-taskparams-bld-langprefix>`,
:ref:`unique-qmpaths<buildconf-taskparams-unique-qmpaths>`,
:ref:`install-langdir<buildconf-taskparams-install-langdir>`.

There are also several additional environment variables for Qt5 toolkit such as:
:ref:`QT5_BINDIR<envvars-qt5bindir>`,
:ref:`QT5_SEARCH_ROOT<envvars-qt5searchroot>`,
:ref:`QT5_LIBDIR<envvars-qt5libdir>` and some others.

ZenMake tries to find Qt5 with ``qmake`` and searches for it in
``QT5_SEARCH_ROOT`` and in the
system ``PATH`` environment variables.
You can use ``QT5_BINDIR`` to set directory path
with ``qmake`` in it.
The ``PATH`` and ``QT5_SEARCH_ROOT`` environment variables are ignored
in this case.

You can specify minimum/maximum version of Qt5 with the
:ref:`QT5_MIN_VER<envvars-qt5minver>` and :ref:`QT5_MAX_VER<envvars-qt5maxver>`
environment variables.

To specify needed Qt5 modules you should use the
:ref:`use<buildconf-taskparams-use>` parameter like this:

.. code-block:: yaml

  use : QtWidgets QtDBus # original title case of Qt5 modules must be used

ZenMake always adds ``QtCore`` module to the ``use`` for tasks with ``qt5``
in :ref:`features<buildconf-taskparams-features>` because every
other Qt5 module depends on ``QtCore`` module.
So you don't need to specify ``QtCore`` to the ``use`` parameter.

Simple Qt5 task can be like that:

.. code-block:: yaml

  tasks:
    myqt5app:
      features  : cxxprogram qt5
      source    : prog/**/*.cpp prog/**/*.qrc prog/**/*.ui prog/**/*.ts
      moc       : prog/**/*.h
      use       : QtWidgets

Also it is recommended to look at examples in the ``qt5`` directory
in the repository `here <repo_demo_projects_>`_.
