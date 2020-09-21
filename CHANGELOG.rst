
Changelog
=========

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