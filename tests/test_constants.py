# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import tests.common as cmn
from waflib import Configure, Build, Context
from zm import constants, starter

def testAll():
    assert constants.WAF_CONFIG_LOG == Configure.WAF_CONFIG_LOG
    assert constants.WAF_CACHE_DIRNAME == Build.CACHE_DIR
    assert constants.WAF_CACHE_NAMESUFFIX == Build.CACHE_SUFFIX
    assert constants.WAF_CFG_FILES_ENV_KEY == Build.CFG_FILES
    assert set(['linux', 'windows', 'darwin']) <= set(constants.KNOWN_PLATFORMS)
    assert constants.PLATFORM in constants.KNOWN_PLATFORMS
