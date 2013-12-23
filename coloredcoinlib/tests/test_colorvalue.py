#!/usr/bin/env python

import unittest

from coloredcoinlib.colorvalue import (SimpleColorValue,
                                       IncompatibleTypesError)
from coloredcoinlib.colordef import POBColorDefinition, OBColorDefinition

 
class TestColorValue(unittest.TestCase):
    def setUp(self):
        self.colordef1 = POBColorDefinition(
            1, {'txhash': 'genesis', 'outindex': 0})
        self.colordef2 = OBColorDefinition(
            2, {'txhash': 'genesis', 'outindex': 0})
        self.cv1 = SimpleColorValue(colordef=self.colordef1,
                                    value=1, label='test')
        self.cv2 = SimpleColorValue(colordef=self.colordef1,
                                    value=2, label='test2')
        self.cv3 = SimpleColorValue(colordef=self.colordef2,
                                    value=1)

    def test_add(self):
        cv4 = self.cv1 + self.cv2
        self.assertEqual(cv4.get_value(), 3)
        cv4 = 0 + self.cv1
        self.assertEqual(cv4.get_value(), 1)
        self.assertRaises(IncompatibleTypesError, self.cv1.__add__,
                          self.cv3)

    def test_iadd(self):
        cv = self.cv1.clone()
        cv += self.cv2
        self.assertEqual(cv.get_value(), 3)

    def test_sub(self):
        cv = self.cv2 - self.cv1
        self.assertEqual(cv.get_value(), 1)

    def test_lt(self):
        self.assertTrue(self.cv1 < self.cv2)
        self.assertTrue(self.cv2 > self.cv1)
        self.assertTrue(self.cv2 >= self.cv1)
        self.assertTrue(self.cv2 > 0)

    def test_eq(self):
        self.assertTrue(self.cv1 == self.cv1)
        self.assertTrue(self.cv1 != self.cv2)
        self.assertTrue(self.cv1 != self.cv3)

    def test_label(self):
        self.assertEqual(self.cv1.get_label(), 'test')

    def test_repr(self):
        self.assertEqual(self.cv1.__repr__(), 'test: 1')

    def test_sum(self):
        cvs = [self.cv1, self.cv2, SimpleColorValue(colordef=self.colordef1,
                                                    value=3)]
        self.assertEqual(SimpleColorValue.sum(cvs).get_value(), 6)


if __name__ == '__main__':
    unittest.main()
