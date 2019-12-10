.. _Waf: https://waf.io

ZenMake
=======

|Licence| |Python| |PythonImpl| |PyPI| |Docs| |Travis| |coveralls|
|ProjectStatus|

ZenMake is a build system based on the meta build system/framework Waf_.
The main purpose of ZenMake is to be as simple to use as possible
but remain flexible.

Main features
-------------

- Easy to use and flexible build config as python (.py) or as yaml file.
- Distribution as zip application or as system package (pip).
- Automatic build order and dependencies. (Thanks to Waf)
- Automatic reconfiguring: no need to run command 'configure'.
- Compiler autodetection. (Thanks to Waf)
- Building and running functional/unit tests including a possibility to
  build and run tests only on changes.
- Running custom scripts during a build phase.
- Build configs in sub directories.
- Supported platforms: GNU/Linux, MacOS, MS Windows. Some other
  platforms like OpenBSD/FreeBSD should be work as well but they
  haven’t been tested.
- Supported languages:

  - C: gcc, clang, msvc, icc, xlc, suncc, irixcc
  - C++: g++, clang++, msvc, icpc, xlc++, sunc++
  - Assembler: gas (GNU Assembler), nasm (experimental)

Documentation
-------------

For full documentation, including installation, tutorials and PDF documents,
please see https://zenmake.readthedocs.io

Project links
-------------

- Main git repository: https://github.com/pustotnik/zenmake
- Mirror git repository: https://gitlab.com/pustotnik/zenmake
- Issue tracker: https://github.com/pustotnik/zenmake/issues
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
.. |Travis| image:: https://travis-ci.com/pustotnik/zenmake.svg?branch=master
   :target: https://travis-ci.com/pustotnik/zenmake
.. |coveralls| image:: https://coveralls.io/repos/github/pustotnik/zenmake/badge.svg
   :target: https://coveralls.io/github/pustotnik/zenmake
.. |ProjectStatus| image:: https://img.shields.io/pypi/status/zenmake.svg
   :target: https://pypi.org/project/zenmake/
