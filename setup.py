import sys
from setuptools import setup, find_packages

#with open("README.md", "r") as fh:
#    long_description = fh.read()
long_description = 'ZenMake - build system based on WAF'

classifiers = """\
Development Status :: 3 - Alpha
License :: OSI Approved :: BSD License
Environment :: Console
Intended Audience :: Developers
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Programming Language :: Python :: 3
Programming Language :: Python :: 3.4
Programming Language :: Python :: 3.5
Programming Language :: Python :: 3.6
Programming Language :: Python :: 3.7
Programming Language :: Python :: Implementation :: CPython
Programming Language :: Python :: Implementation :: PyPy
Operating System :: POSIX :: Linux
Operating System :: MacOS
Operating System :: Microsoft :: Windows
Topic :: Software Development :: Build Tools
"""

classifiers = classifiers.splitlines()

python_requires = '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, <4'

setup(
    name = 'zenmake',
    version = '0.0.2',
    description = 'ZenMake - build system based on WAF',
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = 'https://gitlab.com/pustotnik/zenmake',
    author = 'Alexander Magola',
    author_email = 'pustotnik@gmail.com',
    packages = [],
    classifiers = classifiers,
    python_requires = python_requires,
)
