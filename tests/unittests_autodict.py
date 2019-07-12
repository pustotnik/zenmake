#!/usr/bin/env python
# coding=utf-8
#

# pylint: skip-file

"""
 Copyright (c) 2019, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import unittest
import tests.common as cmn
import zm.autodict

class TestAutoDict(unittest.TestCase):

    def setUp(self):
        self.longMessage = True

    def testAll(self):
        d = zm.autodict.AutoDict()
        d['test'] = 10
        self.assertDictEqual(d, {'test' : 10})
        self.assertTrue(hasattr(d, 'test'))
        self.assertEqual(d['test'], d.test)

        self.assertNotIn('something', d)
        d.something = 123
        self.assertIn('something', d)

        self.assertFalse(d.test2)
        self.assertFalse(d['test3'].test4)

        d2 = zm.autodict.AutoDict(dict(a = 1, b =2))
        self.assertDictEqual(d2, dict(a = 1, b =2))