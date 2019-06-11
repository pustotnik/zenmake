# coding=utf8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD, see LICENSE for more details.
"""

import os

def unfoldPath(cwd, path):
    if not path:
        return path

    if not os.path.isabs(path):
        path = os.path.join(cwd, path)

    path = os.path.expandvars(path)
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    return os.path.normpath(path)

def mksymlink(src, dst, force = True):
    """
    Make symlink, force delete if destination exists already
    """
    if force and (os.path.exists(dst) or os.path.lexists(dst)):
        os.unlink(dst)
    os.symlink(src, dst)

def platform():
    from waflib.Utils import unversioned_sys_platform
    result = unversioned_sys_platform()
    if result.startswith('win32'):
        result = 'windows'
    return result