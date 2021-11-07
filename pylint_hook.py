# coding=utf-8
#
# pylint: skip-file

import sys
import astroid.bases

astroid.bases.POSSIBLE_PROPERTIES.add("cachedprop")

sys.path.insert(1, "src/zenmake")
sys.path.insert(1, "src/zenmake/waf")
sys.path.insert(1, "src/zenmake/thirdparty")
