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

    - GCC C (gcc): regularly tested

    - CLANG C from LLVM (clang): regularly tested

    - Microsoft Visual C/C++ (msvc): regularly tested

    - Intel C/C++ (icc): should work but not tested

    - IBM XL C/C++ (xlc): should work but not tested

    - Oracle/Sun C (suncc): should work but not tested

    - IRIX/MIPSpro C (irixcc): may be works, not tested

  - C++:

    - GCC C++ (g++): regularly tested

    - CLANG C++ from LLVM (clang++): regularly tested

    - Microsoft Visual C/C++ (msvc): regularly tested

    - Intel C/C++ (icpc): should work but not tested

    - IBM XL C/C++ (xlc++): should work but not tested

    - Oracle/Sun C++ (sunc++): should work but not tested

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
  - There is no support for D package manager DUB.

While nobody uses ZenMake for D, there are no plans to resolve these issues.

Supported compilers:

  - DMD Compiler - official D compiler (dmd): regularly tested

  - GCC D Compiler (gdc): regularly tested

  - LLVM D compiler (ldc2): regularly tested

Examples of projects can be found in the directory ``d``
in the repository `here <repo_demo_projects_>`_.

FORTRAN
-----------
  ZenMake supports compiling for Fortran language.

  Supported compilers:

    - GCC Fortran Compiler (gfortran): regularly tested

    - Intel Fortran Compiler (ifort): should work but not tested

Examples of projects can be found in the directory ``fortran``
in the repository `here <repo_demo_projects_>`_.
