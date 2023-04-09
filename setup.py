

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import os
import sys
import shutil
import fnmatch
import subprocess
if sys.hexversion < 0x3050000:
    raise ImportError('Python >= 3.5 is required')

from setuptools import setup
from setuptools import Command
from setuptools.command.egg_info import egg_info as _egg_info
#from wheel.bdist_wheel import bdist_wheel

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)

SRC_DIR = 'src'
DEST_DIR = 'dist'
DIST_DIR = os.path.join(DEST_DIR, 'dist')
DEMOS_DIRPATH = os.path.join(here, 'demos')

sys.path.append(os.path.join(here, SRC_DIR))
from zenmake.zm import version
from zenmake.zm.constants import APPNAME, CAP_APPNAME, AUTHOR, BUILDCONF_FILENAMES

PYPI_USER = 'pustotnik'

AUTHOR_EMAIL = 'pustotnik@gmail.com'

REPO_URL   = 'https://github.com/pustotnik/zenmake'
SRC_URL    = REPO_URL
ISSUES_URL = 'https://github.com/pustotnik/zenmake/issues'
DOCS_URL = 'https://zenmake.readthedocs.io'

DESCRIPTION = '%s - build system based on the WAF' % CAP_APPNAME
with open(os.path.join(here, "README.rst"), "r") as fh:
    LONG_DESCRIPTION = fh.read()

CLASSIFIERS = """\
Development Status :: 4 - Beta
License :: OSI Approved :: BSD License
Environment :: Console
Intended Audience :: Developers
Programming Language :: Python
Programming Language :: Python :: 3 :: Only
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Programming Language :: Python :: 3.8
Programming Language :: Python :: 3.9
Programming Language :: Python :: 3.10
Programming Language :: Python :: 3.11
Programming Language :: Python :: Implementation :: CPython
Operating System :: POSIX :: Linux
Operating System :: MacOS
Operating System :: Microsoft :: Windows
Topic :: Software Development :: Build Tools
""".splitlines()

PYTHON_REQUIRES = '>=3.5'
RUNTIME_DEPS = ['PyYAML']

PKG_DIRS = [APPNAME]

CMD_OPTS = dict(
    # options for commands

    # setuptools/distuils like to litter in several dirs, not one
    egg_info = dict( egg_base = DEST_DIR ),
    sdist = dict( dist_dir = DIST_DIR),
    bdist = dict( dist_dir = DIST_DIR),
    build = dict( build_base = os.path.join(DEST_DIR, 'build')),
    # this is for pure python project which natively supports both python 2 and 3
    # but python 2 was dropped
    #bdist_wheel = dict( universal = 1),
)

class egg_info(_egg_info):

    def finalize_options(self):
        # original 'egg_info' doesn't make dir for self.egg_base
        if self.egg_base and not os.path.isdir(self.egg_base):
            os.makedirs(self.egg_base)
        _egg_info.finalize_options(self)

class clean(Command):

    description = "clean up files from 'setuptools' commands and some extras"

    PATTERNS = '*.pyc *.pyo *.egg-info __pycache__ .pytest_cache .coverage'.split()
    TOP_DIRS = 'build dist'.split() + [DEST_DIR]

    # Support the "all" option. Setuptools expects it in some situations.
    user_options = [
        ('all', 'a', "provided for compatibility"),
    ]

    boolean_options = ['all']

    def initialize_options(self):
        self.all = None

    def finalize_options(self):
        pass

    def clean_builddirs(self, startdir):
        python = sys.executable if sys.executable else 'python'
        zmdir = os.path.join(here, SRC_DIR, 'zenmake')
        devnull = open(os.devnull, 'w')
        for dirpath, _, filenames in os.walk(startdir):
            if not any(x in BUILDCONF_FILENAMES for x in filenames):
                continue
            print('Clean up %r ...' % os.path.relpath(dirpath, here))
            cmdline = [python, zmdir, 'distclean']
            subprocess.call(cmdline, cwd = dirpath, stdout = devnull)

    def run(self):

        self.clean_builddirs(DEMOS_DIRPATH)

        remove = []
        for root, dirs, files in os.walk(here):
            for pattern in self.PATTERNS:
                for name in fnmatch.filter(dirs, pattern):
                    remove.append(os.path.join(root, name))
                    dirs.remove(name) # don't visit sub directories
                for name in fnmatch.filter(files, pattern):
                    remove.append(os.path.join(root, name))

        for path in self.TOP_DIRS:
            remove.append(os.path.join(here, path))

        # remove all
        for path in remove:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors = True)
            elif os.path.isfile(path):
                os.remove(path)

class publish(Command):

    description = "upload to pypi using 'twine'"

    user_options = [
        ('username=', 'u',
        "username for https://upload.pypi.org/legacy/ [default: %s]" % PYPI_USER),
    ]

    def initialize_options(self):
        self.username = None

    def finalize_options(self):
        try:
            import twine
        except ImportError:
            raise ImportError("Module 'twine' not found. You need to install it.")

        if self.username is None:
            self.username = PYPI_USER

    def run(self):
        python = shutil.which('python3')
        if not python:
            python = sys.executable
        cmd = "%s -m twine upload -u %s %s/*" % (python, self.username, DIST_DIR)
        subprocess.call(cmd, shell = True)

cmdclass = {
    'egg_info' : egg_info,
    'clean': clean,
    'publish' : publish,
}

kwargs = dict(
    name = APPNAME,
    version = version.current(),
    license = 'BSD',
    description = DESCRIPTION,
    long_description = LONG_DESCRIPTION,
    #long_description_content_type = "text/markdown",
    long_description_content_type = "text/x-rst",
    url = REPO_URL,
    author = AUTHOR,
    author_email = AUTHOR_EMAIL,
    # It can be True, but by default it's False due to performance reason
    zip_safe = False,
    packages = PKG_DIRS,
    include_package_data = True,    # include everything in source control
    #exclude_package_data = {'': ['README.txt']},
    package_dir = {'': 'src'},
    classifiers = CLASSIFIERS,
    python_requires = PYTHON_REQUIRES,
    install_requires = RUNTIME_DEPS,
    project_urls = {
        'Bug Tracker' : ISSUES_URL,
        'Source Code' : SRC_URL,
        'Documentation' : DOCS_URL,
    },
    entry_points = {
        'console_scripts': [
            '%s = %s.zmrun:main' % (APPNAME, APPNAME),
        ],
    },
    #py_modules = ['__main__'],
    options = CMD_OPTS,
    cmdclass = cmdclass,
)

DEFAULT_SETUP_CMDS = 'clean sdist bdist_wheel'

def main():

    if len(sys.argv) == 1:
        sys.argv.extend(DEFAULT_SETUP_CMDS.split())

    setup(**kwargs)

if __name__ == '__main__':
    main()
