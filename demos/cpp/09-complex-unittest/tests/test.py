#!/usr/bin/env python
# encoding: utf-8

import sys
import os

print('test from a python script')
print('current dir: %s' % os.getcwd() )
print('JUST_ENV_VAR = %s' % os.environ.get('JUST_ENV_VAR', 'does not exist'))
if os.environ.get('RUN_FAILED', False):
    print('failed')
    sys.exit(1)
else:
    print('success')
    sys.exit(0)
