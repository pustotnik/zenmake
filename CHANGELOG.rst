
Changelog
=========

Version 0.11.0 (2022-09-04)
----------------------------

Added
    - embed pyyaml
    - add value 'all' for variable 'for' in the 'byfilter' parameter
    - add buildconf parameter export-* for libpath, stlibpath and all \*flags
    - add the 'cleanall' command as replacement for the 'distclean' command
    - remake/improve/extend substitutions (buildconf variables inside a text)
    - add some syntactic sugar for buildconf
    - get rid of ${TARGET} and rewrite substitution of ${SRC} and ${TGT}
    - add ability to use 'and', 'or' and 'not' in the '\*.select'
    - add 'host-os' and 'distro' for the '\*.select' conditions
    - add 'if' for the 'byfilter' parameter
    - add the 'run' command
    - support qt5 for c++ (almost done) #31
    - enable absolute paths in path patterns
    - add runtime lib paths for the 'run' command and for the 'run' feature
    - support python 3.10

Changed
    - update waf to 2.0.23
    - fix bug with auto detection of interpreter in 'runcmd'
    - rename 'include' to 'incl' and 'exclude' to 'excl' for buildconf parameter 'source'
    - rename buildconf parameter 'matrix' to 'byfilter'
    - rename 'export-config-actions' to 'export-config-results'
    - rename buildconf parameter 'config-actions' to 'configure'
    - remake and improve the buildconf parameters 'export-*'
    - prioritize yaml buildconf format
    - fix bug of no automatic reconfiguration with changed env/cli args for install/uninstall
    - rename buildconf 'features' to 'general'
    - fix bug with 'enabled.select'
    - improve buildconf validator
    - extend/improve install directory vars
    - fix problem when not all values from buildconf.cliopts have effect
    - fix order of reading config values from env, cli and config file
    - fix terminal width detection in CLI
    - improve system libraries detection
    - fix bug when zenmake could not find toolchain from sys env vars like CC, CXX, etc
    - fix problem with found zero-byte executables (mostly windows problem)
    - fix problem with short file names (8.3 filename) on windows
    - fix bug when getting rid of CXX in cmd line does not induce reconfigure
    - make stop child procces in the 'run' command on keyboard interrupt
    - many other fixes

Removed
    - drop python 2.x, 3.4 and pypy
    - remove task features aliases: more problems than profits
    - remove redundant 'default-buildtype' parameter
    - remove the 'platforms' parameter

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