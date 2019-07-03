import sys
from setuptools import setup, find_packages

#with open("README.md", "r") as fh:
#    long_description = fh.read()
long_description = 'ZenMake - build system based on WAF'

setup(
    name='zenmake',
    version='0.0.1',
    description='ZenMake - build system based on WAF',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/pustotnik/zenmake',
    author='Alexander Magola',
    author_email='pustotnik@gmail.com',
    packages=[],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: BSD License',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Operating System :: POSIX :: Linux',
        'Topic :: Software Development :: Build Tools',
    ],
)