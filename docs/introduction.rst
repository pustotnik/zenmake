.. include:: global.rst.inc
.. _introduction:

Introduction
============

What is it?
-----------

ZenMake is a build system based on the meta build system/framework Waf_.
Main purpose of the project is to be as simple as possible to use
but be flexible.

Details about reasons to create this project can be found :ref:`here<why>`.

Main features
-------------
    - Easy to use and flexible build config as python (.py) or as yaml file.
      Details are :ref:`here<buildconf>`.
    - Distribution as zip application or as system package (pip).
      See :ref:`Installation<installation>`.
    - Automatic build order and dependencies. (Thanks to Waf_)
    - Automatic reconfiguring: no need to run command 'configure'.
    - Possibility to autodetect a compiler. (Thanks to Waf_)
    - Building and running functional/unit tests including possibility to
      build and run tests only on changes. Details are :ref:`here<buildtests>`.
    - Running custom scripts during build phase.
    - Supported platforms: GNU/Linux, MacOS, MS Windows. Also some other
      platforms like OpenBSD/FreeBSD should be supported but they aren't tested.
    - Supported languages:

      - C: gcc, clang, msvc, icc, xlc, suncc, irixcc
      - C++: g++, clang++, msvc, icpc, xlc++, sunc++
      - Assembler: gas (GNU Assembler), nasm/yasm (experimental)

Plans to do
------------

There is no clear roadmap for this project. I add features that I think are
needed to include. Also I'm ready to consider user requests to
add/change something.

Project links
-------------

.. include:: projectlinks.rst
