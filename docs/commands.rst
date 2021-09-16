.. include:: global.rst.inc
.. highlight:: console
.. _commands:

Commands
=====================

Here are some descriptions of general commands. You can get the list of the all
commands with a short description by ``zenmake help`` or ``zenmake --help``.
To get help on selected command you
can use ``zenmake help <selected command>`` or
``zenmake <selected command> --help``. Some commands have short aliases.
For example you can use ``bld`` instead of ``build`` and ``dc``
instead of ``distclean``.

configure
    Configure a project. In most cases you don't need to call this command
    directly. The ``build`` command calls this command by itself if necessary.
    This command processes most of values from :ref:`buildconf<buildconf>`
    of a project. Any change in :ref:`buildconf<buildconf>` leads to call
    of this command. You can change this behaviour with parameter ``autoconfig``
    in buildconf :ref:`general features<buildconf-general>`.

build
    Build a project in the current directory. It's the main command. To see all
    possible parameters use ``zenmake help build`` or
    ``zenmake build --help``. For example you can use ``-v`` to see more info
    about building process or ``-p`` to use progress bar instead of text logging.
    By default it calls the ``configure`` command by itself if necessary.

test
    Build and run tests in the current directory. If current project has no tests
    it's almost the same as running the ``build`` command.
    The ``test`` command builds and runs tests by default while
    the ``build`` command doesn't.

clean
    Remove build files for selected ``buildtype`` of a project.
    It doesn't touch other build files.

cleanall
    Remove a build directory of a project with everything in it.

install
    Install the build targets in some destination directory using installation
    prefix. It builds targets by itself if necessary.
    You can control paths with :ref:`environment variables<envvars>`
    or command line parameters (see ``zenmake help install``).
    It looks like classic ``make install`` in common.

uninstall
    Remove the build targets installed with the ``install`` command.
