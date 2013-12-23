#!/usr/bin/env python

import os
import unittest

from coloredcoinlib.toposort import toposorted


class TestSort(unittest.TestCase):
    def setUp(self):
        self.a = 'a'
        self.b = 'b'
        self.l = [self.a, self.b]

    def test_toposort(self):
        def get_all(x):
            return self.l
        self.assertRaises(ValueError, toposorted, self.l, get_all)
        def get_a(x):
            if x == 'a':
                return ['b']
            return []
        self.assertEquals(toposorted(self.l, get_a), ['b', 'a'])

if __name__ == '__main__':
    unittest.main()
