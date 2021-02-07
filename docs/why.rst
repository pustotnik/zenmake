.. include:: global.rst.inc
.. highlight:: none
.. _why:

Why?
============

Short answer: because I could and wanted.

Long answer is below.

https://news.ycombinator.com/item?id=18789162

::

    Cool. One more "new" build system...

Yes, I know, we already have a lot of them. I decided to create this project
because I couldn’t find a build tool for Linux which is quick and easy to use,
flexible, ready to use, with declarative configuration, without the need to learn one more
special language and suitable for my needs.
I know about lots of build systems and I have tried some of them.

Well, a little story of the project. In 2010 year I developed a build system in a
company where I was working that time. It was a build system based on Waf and it was
used successfully for linux projects several years. But that system had a lot of
internal problems and I wanted to remake it from scratch.
And in `2013 <https://bitbucket.org/pustotnik/zenmake.old/src/master/>`_
year I tried to begin a new project. But I had no time to develop it at that time.
Then, in 2019 year I decided to make some own opensorce project and was selecting
a build system for my project. I was considering only opensource cross-platform build
systems that can build C/C++ projects on GNU/Linux. Firstly I tried CMake, then
Meson and Waf. Also I was looking at some other build systems like Bazel.
Eventually, I concluded that I had to try to make my own build tool.

I would do it mostly for myself, but I would be glad if my tool was useful
for others.

..
  All text below was hiding and TAB was added

  Below there is very small comparison of ZenMake with some of existing popular
  build systems. Remember, it's not complete technical comparison.

  **CMake**

  - ZenMake uses YAML and/or python language for build config files. CMake uses own language.
  - ZenMake uses mostly declarative syntax. CMake uses imperative syntax.
  - ZenMake can be used as embedded build system or as installed in an OS build system.
    CMake must be installed in an OS.
  - ZenMake supports gathering of source files with wildcards.
    CMake doesn't recommend to use wildcards due to a problem::

      We do not recommend using GLOB to collect a list of source files from your
      source tree. If no CMakeLists.txt file changes when a source is added or
      removed then the generated build system cannot know when to ask CMake to regenerate.

  **Meson**

  - ZenMake uses YAML and/or python language for build config files.
    Meson uses some dialect of python language.
  - ZenMake can be used as embedded build system or as installed in an OS build system.
    Meson must be installed in an OS.
  - ZenMake supports gathering of source files with wildcards.
    Meson doesn't support wildcards for performance reasons:
    https://mesonbuild.com/FAQ.html#why-cant-i-specify-target-files-with-a-wildcard

  **Bazel**

  - ZenMake uses YAML and/or python language for build config files.
    Bazel uses some dialect of python language with name 'Starlark'.
  - ZenMake can be used as embedded build system or as installed in an OS build system.
    Bazel must be installed in an OS.
  - Bazel is large build system and therefore it almost is not used for
    opensorce projects. ZenMake is small and has minimum dependencies.

  **Waf**

  - ZenMake uses Waf as internal framework.
  - ZenMake uses YAML and/or python language for build config files.
    Waf uses python language.
  - Waf is very flexible but build scripts for Waf are often not easy to create/use
    if you don't know Waf.
    Build configs for ZenMake are easier to create/use.
  - ZenMake can be used as embedded build system or as installed in an OS build system.
    Waf is not considered for installing in an OS by the author of Waf.

  There are many other build systems like Make, Autotools, SCons, xmake, etc.
  But I was lazy to make comparison for all existing build systems.
  Anyway ZenMake is very young project and has no large number of features.