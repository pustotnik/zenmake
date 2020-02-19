.. include:: global.rst.inc
.. _languages:

Supported languages
===================

C/C++
-----------

C an C++ are main languages that ZenMake supports.
And the most of ZenMake features were made for these languages.

Supported compilers:

  - C:

    - regularly tested: gcc, clang, msvc
    - should work: icc, xlc, suncc, irixcc

  - C++:

    - regularly tested: g++, clang++, msvc
    - should work: icpc, xlc++, sunc++

Examples of projects can be found in the directory ``c``  and ``cpp``
in the repository `here <repo_demo_projects_>`_.

Assembler
-----------

ZenMake supports gas (GNU Assembler) and has experimental support for nasm/yasm.

Examples of projects can be found in the directory ``asm``
in the repository `here <repo_demo_projects_>`_.

D
-----------

ZenMake supports compiling for D language. You can configure and build D code
like C/C++ code but there are some limits:

  - There is no support for MS Windows yet.
  - There is no supports for D package manager DUB.

While nobody uses ZenMake for D, there are no plans to solve these problems.

Supported compilers: dmd, gdc, ldc2

Examples of projects can be found in the directory ``d``
in the repository `here <repo_demo_projects_>`_.
