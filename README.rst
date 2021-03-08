
ZenMake
=======

|Licence| |Python| |PythonImpl| |PyPI| |Docs| |GithubCI| |coveralls|
|ProjectStatus|

ZenMake is a cross-platform build system for C/C++ and some other languages.

Main features
-------------

- Build config as python (.py) or as yaml file.
- Distribution as zip application or as system package (pip).
- Automatic reconfiguring: no need to run command 'configure'.
- Compiler autodetection.
- Building and running functional/unit tests including an ability to
  build and run tests only on changes.
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

Documentation
-------------

For full documentation, including installation, tutorials and PDF documents,
please see https://zenmake.readthedocs.io

Project links
-------------

- Primary git repository: https://gitlab.com/pustotnik/zenmake
- Secondary git repository: https://github.com/pustotnik/zenmake
- Issue tracker: https://gitlab.com/pustotnik/zenmake/issues
- Pypi package: https://pypi.org/project/zenmake
- Documentation: https://zenmake.readthedocs.io

.. |Licence| image:: https://img.shields.io/pypi/l/zenmake.svg
   :target: https://pypi.org/project/zenmake/
.. |Python| image:: https://img.shields.io/pypi/pyversions/zenmake.svg
   :target: https://pypi.org/project/zenmake/
.. |PythonImpl| image:: https://img.shields.io/pypi/implementation/zenmake.svg
   :target: https://pypi.org/project/zenmake/
.. |PyPI| image:: https://img.shields.io/pypi/v/zenmake.svg
   :target: https://pypi.org/project/zenmake/
.. |Docs| image:: https://readthedocs.org/projects/zenmake/badge/?version=latest
   :target: https://zenmake.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status
.. |GithubCI| image:: https://img.shields.io/github/workflow/status/pustotnik/zenmake/CI
   :target: https://github.com/pustotnik/zenmake/actions
   :alt: GitHub Workflow CI Status
.. |coveralls| image:: https://coveralls.io/repos/github/pustotnik/zenmake/badge.svg
   :target: https://coveralls.io/github/pustotnik/zenmake
.. |ProjectStatus| image:: https://img.shields.io/pypi/status/zenmake.svg
   :target: https://pypi.org/project/zenmake/
