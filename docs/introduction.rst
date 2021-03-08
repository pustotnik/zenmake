.. include:: global.rst.inc
.. _introduction:

Introduction
============

What is it?
-----------

ZenMake is a cross-platform build system for C/C++ and some other languages.
It uses meta build system Waf_ as a framework.

Some reasons to create this project can be found :ref:`here<why>`.

It uses declarative configuration files with ability to use the real
programming language (python).

Main features
-------------
    - Build config as python (.py) or as yaml file.
      Details are :ref:`here<buildconf>`.
    - Distribution as zip application or as system package (pip).
      See :ref:`Installation<installation>`.
    - Automatic reconfiguring: no need to run command 'configure'.
    - Compiler autodetection.
    - Building and running functional/unit tests including an ability to
      build and run tests only on changes. Details are :ref:`here<buildtests>`.
    - Build configs in sub directories.
    - Building external dependencies.
    - Supported platforms: GNU/Linux, MacOS, MS Windows. Some other
      platforms like OpenBSD/FreeBSD should work as well but it
      hasn't been tested.
    - Supported languages:

      - C: gcc, clang, msvc, icc, xlc, suncc, irixcc
      - C++: g++, clang++, msvc, icpc, xlc++, sunc++
      - D: dmd, ldc2, gdc; MS Windows is not supported yet
      - Fortran: gfortran, ifort (should work but not tested)
      - Assembler: gas (GNU Assembler)

Plans to do
------------

There is no clear roadmap for this project. I add features that I think are
needed to include.

Project links
-------------

.. include:: projectlinks.rst
