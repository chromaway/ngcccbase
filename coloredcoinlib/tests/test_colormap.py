#!/usr/bin/env python

import unittest

from coloredcoinlib.colormap import ColorMap
from coloredcoinlib.colordef import UNCOLORED_MARKER
from coloredcoinlib.txspec import InvalidColorIdError


class MockStore:
    def __init__(self):
        self.d = {}
        self.r = {}
        for i in range(1,10):
            s = "obc:color_desc_%s:0:%s" % (i,i // 2)
            self.d[i] = s
            self.r[s] = i

    def find_color_desc(self, color_id):
        return self.d.get(color_id)

    def resolve_color_desc(self, color_desc, auto_add=True):
        return self.r.get(color_desc)


class MockColorMap(ColorMap):

    def __init__(self, mockstore=None):
        if mockstore is None:
            mockstore = MockStore()
        super(MockColorMap, self).__init__(mockstore)
        self.d = self.metastore.d


class TestColorMap(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()

    def test_find_color_desc(self):
        self.assertEqual(self.colormap.find_color_desc(0), "")
        self.assertEqual(self.colormap.find_color_desc(1),
                         "obc:color_desc_1:0:0")

    def test_resolve_color_desc(self):
        self.assertEqual(self.colormap.resolve_color_desc(""), 0)
        self.assertEqual(self.colormap.resolve_color_desc(
                "obc:color_desc_1:0:0"), 1)

    def test_get_color_def(self):
        self.assertEqual(self.colormap.get_color_def(0), UNCOLORED_MARKER)
        self.assertEqual(self.colormap.get_color_def(1).get_color_id(), 1)
        self.assertEqual(self.colormap.get_color_def(
                "obc:color_desc_1:0:0").get_color_id(), 1)
        self.assertRaises(InvalidColorIdError, self.colormap.get_color_def, 11)


if __name__ == '__main__':
    unittest.main()
