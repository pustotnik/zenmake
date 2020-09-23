
Changelog
=========

Version 0.10.0 (2020-09-23)
----------------------------

Added
    - support Fortran language
    - add basic D language support
    - add selectable parameters for buildconf task parameters
    - support external dependencies
    - add 'tryall' and 'after'/'before' for parallel configuration actions
    - add correct buildconf validation for nested types
    - add configuration action 'call-pyfunc' ('check-by-pyfunc') to parallel actions
    - add configuration action 'check-code'
    - add configuration actions 'pkgconfig' and 'toolconfig' (support pkg-config and other \*-config tools)
    - add configuration action 'find-file'
    - add 'remove-defines' for configuration action 'write-config-header'
    - add option to add extra files to monitor ('monitor-files')
    - add buildconf task parameters 'stlibs' and 'stlibpath'
    - add buildconf task parameters 'monitlibs' and 'monitstlibs'
    - add buildconf task parameter 'export-config-actions'
    - add buildconf task parameter 'enabled'
    - add buildconf task parameter 'group-dependent-tasks'
    - add add buildconf task parameter 'install-files'
    - add parameter 'build-work-dir-name' to buildconf 'features'
    - add simplified form of patterns using for buildconf task parameter 'source'
    - add custom substitution variables
    - add detection of msvc, gfortran, ifort and D compilers for command 'sysinfo'
    - add number of CPUs for command 'sysinfo'
    - add 'not-for' condition for config var 'matrix'
    - add ability to set compiler flags in buildconf parameter 'toolchains'
    - add ability to use 'run' in buildconf as a string or function
    - add cdmline options --verbose-configure (-A) and --verbose-build (-B)
    - add cmdline option '--force-edeps'
    - add c++ demo project with boost libraries
    - add demo project with luac
    - add demo project with 'strip' utility on linux
    - add demo project with dbus-binding-tool
    - add demo projects for gtk3
    - add demo project for sdl2
    - add codegen demo project

Changed
    - improve support of spaces in values (paths, etc)
    - improve unicode support
    - use sha1 by default for hashes
    - correct some english text in documentation
    - detach build obj files from target files
    - remove locks in parallel configuration actions
    - small optimization of configuration actions
    - improve validation for parallel configuration actions
    - improve error handling for configuration actions with python funcs
    - improve buildconf errors handling
    - improve use of buildconf parameter 'project.version'
    - remake/improve handling of cache/db files (see buildconf parameter 'db-format')
    - reduce size of zenmake.pyz by ignoring some unused waf modules
    - apply solution from waf issue 2272 to fix max path limit on windows with msvc
    - rename '--build-tests' to '--with-tests', enable it for 'configure' and add ability to use -t and -T as flags
    - rename 'sys-lib-path' to 'libpath' and fix bug with incorrect value
    - rename 'sys-libs' to 'libs'
    - rename 'conftests' to 'config-actions'
    - rename config action 'check-programs' to 'find-program' and change behaviour
    - make ordered configuration actions
    - disable ':' in task names
    - refactor code to support task features in separated python modules
    - don't merge buildconf parameter 'project' in sub buildconfs (see 'subdirs')
    - fix bug with toolchain supported more than one language
    - fix some bugs with env vars
    - fix compiling problem with the same files in different tasks
    - fix bug with object file indexes
    - fix command 'clean' for case when build dir is symlink
    - fix Waf bug of broken 'vnum' for some toolchains
    - fix parsing of cmd line in 'runcmd' on windows
    - fix processing of destdir, prefix, bindir, libdir

Removed
    - remove configuration action (test) 'check'

Version 0.9.0 (2019-12-10)
----------------------------

Added
    - add config parameter 'startdir'
    - add config parameter 'subdirs' to support sub configs
    - add 'buildroot' as the command-line arg and the environment variable
    - print header with some project info
    - add parallel configuration tests

Changed
    - fix default command-line command
    - fix problem of too long paths in configuration tests on Windows
    - fix some small bugs in configuration tests
    - rid of the wscript file during building
    - improve buildconf validator
    - improve checking of the task features
    - update Waf to version 2.0.19

Removed
    - remove config parameters 'project.root' and 'srcroot'