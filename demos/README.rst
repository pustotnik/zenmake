

ZenMake demo projects
=====================

This directory contains demo projects which are used for testing on different
platforms with different toolchains, libraries, etc. Also they demonstrate
use of ZenMake and can be used as examples.

Because these projects are used many different things they have many dependencies.
Full list of actual dependencies which are used for regular testing on travis-ci
can be obtained from file '.travis.yml' in the repository root. Different demo
projects have different dependencies and you need to have all of these
dependencies only if you want to run all these examples.
Not all projects can be run on any platform.

At the time of writing there are following dependencies:

Linux:
    - python
    - pyyaml
    - gcc
    - clang
    - nasm
    - yasm
    - dmd
    - gdc
    - ldc
    - boost
    - lua (5.1)
    - dbus-glib (libdbus-glib-1-dev)
    - gfortran

macOS:
    - python
    - pyyaml
    - clang
    - dmd
    - ldc
    - boost

MS Windows:
    - python 3.x
    - pyyaml
    - msvc (Microsoft Visual C++)
    - boost