#!/usr/bin/env python
# coding=utf-8
#
# pylint: skip-file

"""
Copyright (c) 2019, Alexander Magola
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import io
import re
import subprocess
from distutils.spawn import find_executable as findProg

if sys.hexversion < 0x2070000:
    raise ImportError('Python >= 2.7 is required')

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)

import setup
#sys.path.append(os.path.join(here, setup.SRC_DIR))
from zenmake.zm import pyutils

version = setup.version

GIT_EXE = findProg('git')
PY_EXE = sys.executable

if pyutils.PY3:
    _input = input
else:
    _input = raw_input

def _runInShell(cmd):
    try:
        output = subprocess.check_output(cmd, shell = True)
    except subprocess.CalledProcessError as ex:
        print(ex)
        sys.exit(ex.returncode)
    return output.decode(sys.stdout.encoding)

def _runPyScript(args):
    return _runInShell('%s %s' % (PY_EXE, args))

def _runGitCmd(args):
    return _runInShell('git %s' % args)

def _getAnswerYesNo(question):
    while True:
        answer = _input(question + ' [y/n]')
        if not answer or answer[0] == 'n':
            return False
        if answer != 'y' and answer != 'yes':
            print('Invalid answer %r' % answer)
            continue
        return True

def _writeVersionFile(ver):
    filePath = version.VERSION_FILE_PATH
    with io.open(filePath, 'wt') as file:
        file.write(pyutils.texttype(ver))

def _bumpVersion(ver):

    output = _runGitCmd("tag")
    existingVers = [x[1:] for x in output.split() if x and x[0] == 'v']
    if ver in existingVers:
        print("Version %r already exists in git tags. Stopped." % ver)
        sys.exit(1)

    _writeVersionFile(ver)
    verFilePath = os.path.relpath(version.VERSION_FILE_PATH, here)
    _runGitCmd("add %s" % verFilePath)
    _runGitCmd("commit -m 'bump version'")
    _runGitCmd("tag -a v%s -m 'version %s'" % (ver, ver))
    _runGitCmd("push")
    _runGitCmd("push --tags")

def _writeNewDevVersion(baseVer):
    parsed = version.parseVersion(baseVer)
    gr = parsed.groups()
    nextVer = '.'.join([gr[0], gr[1], str(int(gr[2])+1)])
    nextVer += '-dev'
    _writeVersionFile(nextVer)
    return nextVer

def _checkChangeLog(newVer):
    filePath = os.path.join(here, 'CHANGELOG.rst')
    if not os.path.isfile(filePath):
        print("File %r doesn't exist" % filePath)
        sys.exit(1)

    pattern = 'Version\s+' + newVer
    pattern = re.compile(pattern)
    with io.open(filePath, 'rt') as file:
        for line in file:
            if pattern.search(line):
                break
        else:
            return False

    return True

def main():
    """ do main work """

    cmdArgs = sys.argv[1:]
    if not cmdArgs:
        msg = "There is no version in args. Current version: "
        msg += version.current()
        print(msg)
        if GIT_EXE:
            print("Result of 'git describe': ")
            print(_runGitCmd('describe'))
        msg = "\nUsage: " + sys.argv[0] + " x.y.z where x,y,z are numbers"
        print(msg)
        return 0

    newVer = cmdArgs[0]
    if not version.checkFormat(newVer):
        print('Version %r has invalid format' % newVer)
        return 1

    if not GIT_EXE:
        print("There is no 'git'. Install 'git' to use this script.")
        return 2

    if not _checkChangeLog(newVer):
        print('There is no records for the version %r in changelog file' % newVer)
        return 3

    question = 'Bump version to %s?'
    question += ' It will write the version to file,'
    question += '\nadd it to git repo, commit it and add git tag with the version.'
    answer = _getAnswerYesNo(question % newVer)
    if not answer:
        return 0

    print("Bumping version to %r .." % newVer)
    _bumpVersion(newVer)
    print("Building distribution ..")
    _runPyScript('setup.py clean sdist bdist_wheel')

    answer = _getAnswerYesNo('Distribution was built successfully. Publish it to pypi?')
    if answer:
        print("Publishing distribution ..")
        _runPyScript('setup.py publish')
        print("Distribution was published.")

    print("Writing new dev version to file %r .." % version.VERSION_FILE_PATH)
    nextVer = _writeNewDevVersion(newVer)
    print("New dev version %r was written to file." % nextVer)

    return 0

if __name__ == '__main__':
    sys.exit(main())
