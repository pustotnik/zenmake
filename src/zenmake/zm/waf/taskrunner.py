# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import Runner as WafRunner
from zm.pyutils import asmethod
from zm.utils import SafeCounter

@asmethod(WafRunner.Parallel, '__init__', wrap = True, callOrigFirst = True)
def _parallelInit(self, *_, **__):

    self.taskCounter = SafeCounter()
