# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Errors import WafError as _WafError

verbose = 2

class ZenMakeError(_WafError):
    """Base class for all ZenMake errors"""

    def __init__(self, msg = '', ex = None):
        super(ZenMakeError, self).__init__(msg, ex)
        self.fullmsg = self.verbose_msg

class ZenMakeLogicError(ZenMakeError):
    """Some logic/programming error"""

class ZenMakeConfError(ZenMakeError):
    """Invalid buildconf fle error"""

    def __init__(self, msg = '', ex = None, confpath = None):
        if confpath and msg:
            _msg = "Error in the file %r:" % confpath
            for line in msg.splitlines():
                _msg += "\n  %s" % line
            msg = _msg
        self.confpath = confpath

        if verbose == 0: # optimization
            # pylint: disable = non-parent-init-called
            Exception.__init__(self)
            self.stack = []
            if ex and not msg:
                msg = str(ex)

            self.fullmsg = self.verbose_msg = self.msg = msg
        else:
            super(ZenMakeConfError, self).__init__(msg, ex)

class ZenMakeConfTypeError(ZenMakeConfError):
    """Invalid buildconf param type error"""

class ZenMakeConfValueError(ZenMakeConfError):
    """Invalid buildconf param value error"""

class ZenMakeDirNotFoundError(ZenMakeError):
    """ Directory doesn't exist """

    def __init__(self, path):
        self.path = path
        msg = "Directory %r doesn't exist." % path
        super(ZenMakeDirNotFoundError, self).__init__(msg)

class ZenMakeFileNotFoundError(ZenMakeError):
    """ File doesn't exist """

    def __init__(self, path):
        self.path = path
        msg = "File %r doesn't exist." % path
        super(ZenMakeFileNotFoundError, self).__init__(msg)

class ZenMakeProcessFailed(ZenMakeError):
    """ Process failed with exitcode """

    def __init__(self, cmd, exitcode):
        self.cmd = cmd
        self.exitcode = exitcode
        msg = "Command %r failed with exit code %d." % (cmd, exitcode)
        super(ZenMakeProcessFailed, self).__init__(msg)

class ZenMakeProcessTimeoutExpired(ZenMakeError):
    """ Raised when a timeout expires while waiting for a process """

    def __init__(self, cmd, timeout, output):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output
        msg = "Timeout (%d sec.) for command expired." % timeout
        msg += "\nCommand: %r" % cmd
        if output:
            msg += '\nCaptured output:\n'
            msg += output
        super(ZenMakeProcessTimeoutExpired, self).__init__(msg)
