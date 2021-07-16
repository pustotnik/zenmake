

ZenMake demo projects
=====================

This directory contains demo projects which are used for testing on different
platforms with different toolchains, libraries, etc. Also they demonstrate
use of ZenMake and can be used as examples.

These projects have many dependencies due to use of many different things.
Full list of actual dependencies which are used for regular testing in CI
can be obtained from file 'ci.yml' in the repository directory '.github/workflows'.
Different demo projects have different dependencies and you need to have all of these
dependencies only if you want to run all these examples.
Not every project can be run on all platforms.

At the time of writing there are following dependencies:

Linux:
    - python 3.x
    - pyyaml (optional)
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
    - gtk3 (libgtk-3-dev)
    - sdl2 (libsdl2-dev)

macOS:
    - python 3.x
    - pyyaml (optional)
    - clang
    - dmd
    - ldc
    - boost

MS Windows:
    - python 3.x
    - pyyaml (optional)
    - msvc (Microsoft Visual C++)
    - boost
