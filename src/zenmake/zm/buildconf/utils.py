# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm import utils

def gatherAllTaskNames(buildconf):
    """
    Gather all task names from buildconf.
    Returns set of names
    """

    names = list(buildconf.tasks.keys())
    for entry in buildconf.matrix:
        names.extend(utils.toList(entry.get('for', {}).get('task', [])))
    return set(names)
