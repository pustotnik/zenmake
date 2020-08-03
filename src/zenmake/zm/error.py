# coding=utf-8
#

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from waflib.Errors import WafError

verbose = 2

class ZenMakeError(WafError):
    """Base class for all ZenMake errors"""

    def __init__(self, msg = None, ex = None):
        if msg is None:
            msg = ''
        super(ZenMakeError, self).__init__(msg, ex)
        self.fullmsg = self.verbose_msg

class ZenMakeLogicError(ZenMakeError):
    """Some logic/programming error"""

class ZenMakeConfError(ZenMakeError):
    """Invalid buildconf fle error"""

    def __init__(self, msg = None, ex = None, confpath = None):
        if msg is None:
            msg = ''
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

class ZenMakePathNotFoundError(ZenMakeError):
    """ Path doesn't exist """

    def __init__(self, path, msg = None):
        self.path = path
        if not msg:
            msg = "Path %r doesn't exist." % path
        super(ZenMakePathNotFoundError, self).__init__(msg)

class ZenMakeDirNotFoundError(ZenMakePathNotFoundError):
    """ Directory doesn't exist """

    def __init__(self, path, msg = None):
        if not msg:
            msg = "Directory %r doesn't exist." % path
        super(ZenMakeDirNotFoundError, self).__init__(path, msg)

class ZenMakeProcessFailed(ZenMakeError):
    """ Process failed with exitcode """

    def __init__(self, cmd, exitcode, msg = None):
        self.cmd = cmd
        self.exitcode = exitcode
        if not msg:
            msg = "Command %r failed with exit code %d." % (cmd, exitcode)
        super(ZenMakeProcessFailed, self).__init__(msg)

class ZenMakeProcessTimeoutExpired(ZenMakeError):
    """ Raised when a timeout expires while waiting for a process """

    def __init__(self, cmd, timeout, output, msg = None):
        self.cmd = cmd
        self.timeout = timeout
        self.output = output

        if not msg:
            msg = "Timeout (%d sec.) for command expired." % timeout
            msg += "\nCommand: %r" % cmd
            if output:
                msg += '\nCaptured output:\n'
                msg += output
        super(ZenMakeProcessTimeoutExpired, self).__init__(msg)
