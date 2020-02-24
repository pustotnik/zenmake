# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm import toolchains

toolchains.regToolchains('asm', { 'default': ('gas', 'nasm'), })
