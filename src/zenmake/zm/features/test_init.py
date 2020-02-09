# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

from zm import cli

TASK_FEATURES_SETUP = {
    'test' : {}
}

cli.config.options.extend([
    cli.Option(
        names = ['-t', '--with-tests'],
        dest = 'withTests',
        choices = ('yes', 'no'),
        const = 'yes', # it enables use of option as flag
        nargs = '?', # it's necessary with use of 'const'
        commands = ['configure', 'build', 'test'],
        help = 'include tests',
    ),
    cli.Option(
        names = ['-T', '--run-tests'],
        dest = 'runTests',
        choices = ('all', 'on-changes', 'none'),
        const = 'all', # it enables use of option as flag
        nargs = '?', # it's necessary with use of 'const'
        commands = ['build', 'test'],
        help = 'run tests',
    ),
])

cli.config.optdefaults.update({
    'with-tests' : { 'any': 'no',   'test' : 'yes' },
    'run-tests' : { 'any': 'none', 'test' : 'all' },
})
