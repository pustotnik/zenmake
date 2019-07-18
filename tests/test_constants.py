# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import tests.common as cmn
from waflib import Build, Context
from zm import constants

class TestAutoDict(object):
    def testAll(self):
        assert constants.WAF_CACHE_DIRNAME == Build.CACHE_DIR
        assert constants.WAF_CACHE_NAMESUFFIX == Build.CACHE_SUFFIX
        assert constants.WSCRIPT_NAME == Context.WSCRIPT_FILE