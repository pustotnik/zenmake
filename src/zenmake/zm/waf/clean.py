# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Build import CleanContext as WafCleanContext
from zm.utils import asmethod
from zm.deps import produceExternalDeps

@asmethod(WafCleanContext, 'execute')
def _ctxExecute(self):

    self.restore()
    if not self.all_envs:
        self.load_envs()

    produceExternalDeps(self)

    self.recurse([self.run_dir])
    try:
        self.clean()
    finally:
        self.store()
