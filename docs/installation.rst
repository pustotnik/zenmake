.. include:: global.rst.inc
.. highlight:: console
.. _installation:

Installation
============

**Dependencies**

* Python_ >=3.5. Python must have threading support.
  Python has threading in most cases while nobody uses ``--without-threads``
  for Python building. Python >= 3.7 always has threading.
* `PyYAML <https://pyyaml.org/>`_ It's optional and needed only
  if you use yaml :ref:`buildconf<buildconf>`. ZenMake can be used with yaml
  buildconf file even though there is no PyYAML in a operation system because
  ZenMake has an internal copy of PyYAML python library. This copy is used only
  if there is no PyYAML installed in a operation system.


There are different ways to install/use ZenMake:

.. contents::
   :local:

Via python package (pip)
------------------------
ZenMake has its `own python package <pypipkg_>`_. You can install it by::

    pip install zenmake

In this way pip will install PyYAML if it's not installed already.

.. note::
    ``POSIX``: It requires root and will install it system-wide.
    Alternatively, you can use::

        pip install --user zenmake

    which will install it for your user
    and does not require any special privileges. This will install the package
    in ~/.local/, so you will have to add ~/.local/bin to your PATH.

    ``Windows``: It doesn't always require administrator rights.

.. note::
    You need to have ``pip`` installed. Most of the modern Linux distributions
    have pip in their packages. On Windows you can use, for example,
    `chocolatey <https://chocolatey.org/>`_.
    Common instructions to install pip can be found
    `here <https://pip.pypa.io/en/stable/installing/>`_.

.. note::
    You can install ZenMake with pip and virtualenv_. In this case you don't
    touch system packages and it doesn't require root privileges.

After installing you can run ZenMake just by typing::

    zenmake

.. _installation-via-git:

Via git
----------

You can use ZenMake from Git repository. But branch ``master`` can be
broken. Also, you can just to switch to the required version using git tag. Each
version of ZenMake has a git tag. The body of ZenMake application is located in
``src/zenmake`` path in the repository. You don't need other directories and
files in repository and you can remove them if you want. Then you can make symlink
to ``src/zenmake/zmrun.py``, shell alias or make executable
.sh script (for Linux/MacOS/..) or .bat (for Windows) to
run ZenMake. Example for Linux (``zmrepo`` is custom directory)::

    $ mkdir zmrepo
    $ cd zmrepo
    $ git clone https://gitlab.com/pustotnik/zenmake.git .

Next step is optional. Switch to existing version, for example to 0.7.0::

    $ git checkout v0.7.0

Here you can make symlink/alias/script to run zenmake.

Other options to run ZenMake::

    $ <path-to-zenmake-repo>/src/zenmake/zmrun.py

or::

    $ python <path-to-zenmake-repo>/src/zenmake

As a zip application
------------------------
Zenmake can be run as an executable python zip application. And ZenMake can make
such zipapp with the command ``zipapp``.
Using steps from `Via Git <installation-via-git_>`_ you can run::

    $ python src/zenmake zipapp
    $ ls *.pyz
    zenmake.pyz
    $ ./zenmake.pyz
    ...

Resulting file ``zenmake.pyz`` can be run standalone without the repository and pip.
You can copy ``zenmake.pyz`` to the root of your project and distribute this
file with your project. It can be used on any supported platform and doesn't
require any additional access and changes in your system.

.. note::
    Since ZenMake 0.10.0 you can download ready to use ``zenmake.pyz`` from
    GitHub `releases <github_releases_>`_.

.. _virtualenv: https://pypi.python.org/pypi/virtualenv/
