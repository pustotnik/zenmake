.. include:: global.rst.inc
.. highlight:: console
.. _faq:

FAQ
================================

**Why is python used?**

It's mostly because Waf_ is implemented in python.

**Can I use buildconf.py as usual python script?**

Yes, you can. Such a behavior is supported while you don't try to use
reserved config variable names for inappropriate reasons.

**I want to install my project via zenmake without 'bin' and 'lib64' in one directory**

Example on Linux::

    DESTDIR=your_install_path PREFIX=/ BINDIR=/ LIBDIR=/ zenmake install

or::

    PREFIX=your_install_path BINDIR=your_install_path LIBDIR=your_install_path zenmake install
