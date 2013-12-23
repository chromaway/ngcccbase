#!/usr/bin/env python

import unittest

from coloredcoinlib import ColorSet
from test_colormap import MockColorMap


class TestColorSet(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [''])
        self.colorset1 = ColorSet(self.colormap, [d[1]])
        self.colorset2 = ColorSet(self.colormap, [d[2]])
        self.colorset3 = ColorSet(self.colormap, [d[1], d[2]])
        self.colorset4 = ColorSet(self.colormap, [d[3], d[2]])
        self.colorset5 = ColorSet(self.colormap, [d[3], d[1]])
        self.colorset6 = ColorSet(self.colormap, [])

    def test_repr(self):
        self.assertEquals(self.colorset0.__repr__(), "['']")
        self.assertEquals(self.colorset1.__repr__(),
                          "['obc:color_desc_1:0:0']")
        self.assertEquals(self.colorset3.__repr__(),
                          "['obc:color_desc_1:0:0', 'obc:color_desc_2:0:1']")

    def test_uncolored_only(self):
        self.assertTrue(self.colorset0.uncolored_only())
        self.assertFalse(self.colorset1.uncolored_only())
        self.assertFalse(self.colorset3.uncolored_only())

    def test_get_data(self):
        self.assertEquals(self.colorset0.get_data(), [""])
        self.assertEquals(self.colorset1.get_data(), ["obc:color_desc_1:0:0"])

    def test_get_hash_string(self):
        self.assertEquals(self.colorset0.get_hash_string(), "055539df4a0b804c58caf46c0cd2941af10d64c1395ddd8e50b5f55d945841e6")
        self.assertEquals(self.colorset1.get_hash_string(), "ca90284eaa79e05d5971947382214044fe64f1bdc2e97040cfa9f90da3964a14")
        self.assertEquals(self.colorset3.get_hash_string(), "09f731f25cf5bfaad512d4ee6f37cb9481f442df3263b15725dd1624b4678557")

    def test_get_earliest(self):
        self.assertEquals(self.colorset5.get_earliest(), "obc:color_desc_1:0:0")
        self.assertEquals(self.colorset4.get_earliest(), "obc:color_desc_2:0:1")
        self.assertEquals(self.colorset6.get_earliest(), "\x00\x00\x00\x00")

    def test_get_color_string(self):
        self.assertEquals(self.colorset1.get_color_hash(), "CP4YWLr8aAe4Hn")
        self.assertEquals(self.colorset3.get_color_hash(), "ZUTSoEEwZY6PB")

    def test_has_color_id(self):
        self.assertTrue(self.colorset0.has_color_id(0))
        self.assertTrue(self.colorset3.has_color_id(1))
        self.assertFalse(self.colorset1.has_color_id(0))
        self.assertFalse(self.colorset4.has_color_id(1))

    def test_intersects(self):
        self.assertFalse(self.colorset0.intersects(self.colorset1))
        self.assertTrue(self.colorset1.intersects(self.colorset3))
        self.assertTrue(self.colorset3.intersects(self.colorset1))
        self.assertTrue(self.colorset4.intersects(self.colorset3))
        self.assertFalse(self.colorset2.intersects(self.colorset0))
        self.assertFalse(self.colorset1.intersects(self.colorset4))

    def test_equals(self):
        self.assertFalse(self.colorset1.equals(self.colorset0))
        self.assertTrue(self.colorset3.equals(self.colorset3))
        self.assertFalse(self.colorset4.equals(self.colorset5))
        
    def test_from_color_ids(self):
        self.assertTrue(self.colorset0.equals(
                ColorSet.from_color_ids(self.colormap, [0])))
        self.assertTrue(self.colorset3.equals(
                ColorSet.from_color_ids(self.colormap, [1,2])))
        tmp = ColorSet.from_color_ids(self.colormap, [1,2,3])
        self.assertTrue(tmp.has_color_id(1))
        self.assertTrue(tmp.has_color_id(2))
        self.assertTrue(tmp.has_color_id(3))


if __name__ == '__main__':
    unittest.main()
