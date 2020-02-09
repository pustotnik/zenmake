# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Tools.compiler_c import c_compiler
from zm import toolchains

toolchains.langTable['c'] = c_compiler
