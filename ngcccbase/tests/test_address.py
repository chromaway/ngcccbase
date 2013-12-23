#!/usr/bin/env python

import unittest

from pycoin.encoding import EncodingError, b2a_base58

from coloredcoinlib import ColorSet
from coloredcoinlib.tests.test_colorset import MockColorMap
from ngcccbase.address import LooseAddressRecord, InvalidAddressError


class TestAddress(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [self.colormap.get_color_def(0).__repr__()])
        self.colorset1 = ColorSet(self.colormap, [d[1]])
        self.main_p = '5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF'
        self.main = LooseAddressRecord(address_data=self.main_p,
                                       color_set=self.colorset0,
                                       testnet=False)
        self.test_p = '91avARGdfge8E4tZfYLoxeJ5sGBdNJQH4kvjJoQFacbgyUY4Gk1'
        self.test = LooseAddressRecord(address_data=self.test_p,
                                       color_set=self.colorset1,
                                       testnet=True)


    def test_init(self):
        self.assertEqual(self.main.get_address(),
                         '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj')
        self.assertEqual(self.test.get_address(),
                         'mo3oihY41iwPco1GKwehHPHmxMT4Ld5W3q')
        self.assertRaises(EncodingError, LooseAddressRecord,
                          address_data=self.main_p[:-2] + '88')
        self.assertRaises(EncodingError, LooseAddressRecord,
                          address_data=self.test_p[:-2] + '88',
                          testnet=True)
        self.assertRaises(InvalidAddressError, LooseAddressRecord,
                          address_data=self.main_p, testnet=True)
        self.assertRaises(InvalidAddressError, LooseAddressRecord,
                          address_data=self.test_p, testnet=False)

    def test_get_color_set(self):
        self.assertEqual(self.main.get_color_set().__repr__(),
                         self.colorset0.__repr__())

    def test_get_color_address(self):
        self.assertEqual(self.main.get_color_address(),
                         '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj')
        self.assertEqual(self.test.get_color_address(),
                         'CP4YWLr8aAe4Hn@mo3oihY41iwPco1GKwehHPHmxMT4Ld5W3q')

    def test_get_data(self):
        self.assertEqual(self.main.get_data()['color_set'],
                         self.colorset0.get_data())
        self.assertEqual(self.main.get_data()['address_data'],
                         self.main_p)
        self.assertEqual(self.test.get_data()['color_set'],
                         self.colorset1.get_data())
        self.assertEqual(self.test.get_data()['address_data'],
                         self.test_p)

if __name__ == '__main__':
    unittest.main()

