.. include:: global.rst.inc
.. highlight:: console
.. _commands:

Commands
=====================

Here are some descriptions of main commands. List of all commands with
a short description can be gotten with
``zenmake help`` or ``zenmake --help``. To get help on selected command you
can use ``zenmake help <selected command>`` or
``zenmake <selected comman> --help``. Some commands have short alieses.
For example you can use ``bld`` instead of ``build`` or ``dc``
instead of ``distclean``.

configure
    Configures project. In most cases you don't need to call this command
    directly. Command ``build`` will call this command itself if necessary.
    This command processes most of values of :ref:`buildconf<buildconf>`.
    So any change in :ref:`buildconf<buildconf>` leads to call of this command.

build
    Builds project of the current directory. It's the main command. To see all
    possible parameters use ``zenmake help build`` or
    ``zenmake build --help``. For example you can use ``-v`` to see more info
    about building process or ``-p`` to use progress bar instead of text logging.
    It calls ``configure`` itself if necessary.

test
    Builds and runs tests of the current directory. If no tests it's the same as running
    ``build``. Command ``test`` builds and runs tests by default while
    command ``build`` doesn't.

clean
    Removes build files for selected ``buildtype``. It doesn't touch other
    build files.

distclean
    Removes the build directory with everything in it.

install
    Installs the build targets on the system. It builds targets itself
    if necessary. You can control paths with :ref:`environment variables<envvars>`
    or command line parameters (see ``zenmake help install``).
    In common it looks like classic ``make install``.

uninstall
    Removes the build targets installed with command ``install``.
