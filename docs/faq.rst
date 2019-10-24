.. include:: global.rst.inc
.. highlight:: console
.. _faq:

FAQ
================================

**Why is python used?**

It's mostly because Waf_ is implemented in python.

**Can I use buildconf.py as usual python script?**

Yes, you can. Such a behavior is supported until you don't try to use
reserved config variable names for unappropriated reasons.

**I want to install my project via zenmake without 'bin' and 'lib64' in one directory**

Example on Linux::

    DESTDIR=/tmp/your_install_path BINDIR=/ LIBDIR=/ zenmake install
