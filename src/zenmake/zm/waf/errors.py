# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib import Errors as WafErrors
from zm.utils import asmethod
from zm import error

_TRACEBACK_BEGIN = 'Traceback'

@asmethod(WafErrors.BuildError, 'format_error')
def _formatBuildError(self):

    msglines = ['Build failed']
    for tsk in self.tasks:
        errmsg = tsk.format_error()
        if not errmsg:
            continue

        if error.verbose == 0 and errmsg.startswith(_TRACEBACK_BEGIN):
            # make report without traceback
            taskName = getattr(tsk.generator, 'name', '')
            lines = errmsg.splitlines()[1:]
            for i, line in enumerate(lines):
                if line[0].isspace():
                    continue
                pos = line.find(':')
                errmsg = line[pos + 1:] if pos >= 0 else line
                errmsg = " -> task in %r failed: %s" % (taskName, errmsg)
                break
            else:
                # do nothing with errmsg
                i = len(lines)

            if i + 1 < len(lines):
                errmsg += "\n ->   "
                errmsg += "\n ->   ".join(lines[i + 1:])

        msglines.append(errmsg)

    return "\n".join(msglines)
