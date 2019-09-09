# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import sys
from os import path

ZENMAKE_DIR = path.dirname(path.abspath(__file__))
ZENMAKE_DIR = path.abspath(path.join(ZENMAKE_DIR, path.pardir))
if ZENMAKE_DIR not in sys.path:
    sys.path.insert(0, ZENMAKE_DIR)

WAF_DIR = path.join(ZENMAKE_DIR, 'waf')
if WAF_DIR not in sys.path:
    sys.path.insert(1, WAF_DIR)
