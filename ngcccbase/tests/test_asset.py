#!/usr/bin/env python

import unittest

from coloredcoinlib.tests.test_colorset import MockColorMap
from coloredcoinlib import ColorSet

from ngcccbase.asset import AssetDefinition, AssetDefinitionManager


class MockUTXO:
    def __init__(self, value, cvs):
        self.value = value
        self.colorvalues = cvs

class TestAssetDefinition(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [d[0]])
        self.colorset1 = ColorSet(self.colormap, [d[1], d[2]])
        self.colorset2 = ColorSet(self.colormap, [d[3]])
        self.def0 = {'monikers': ['bitcoin'],
                     'color_set': self.colorset0.get_data(),
                     'unit':100000000}
        self.def1 = {'monikers': ['test1'],
                     'color_set': self.colorset1.get_data(),
                     'unit':10}
        self.def2 = {'monikers': ['test2','test2alt'],
                     'color_set': self.colorset2.get_data(),
                     'unit':1}
        self.asset0 = AssetDefinition(self.colormap, self.def0)
        self.asset1 = AssetDefinition(self.colormap, self.def1)
        self.asset2 = AssetDefinition(self.colormap, self.def2)

        config = {'asset_definitions': [self.def1, self.def2]}
        self.adm = AssetDefinitionManager(self.colormap, config)

    def test_repr(self):
        self.assertEquals(self.asset0.__repr__(), "['bitcoin']: ['']")
        self.assertEquals(
            self.asset1.__repr__(),
            "['test1']: ['obc:color_desc_1:0:0', 'obc:color_desc_2:0:1']")
        self.assertEquals(self.asset2.__repr__(),
                          "['test2', 'test2alt']: ['obc:color_desc_3:0:1']")

    def test_get_monikers(self):
        self.assertEquals(self.asset0.get_monikers(), ['bitcoin'])
        self.assertEquals(self.asset1.get_monikers(), ['test1'])
        self.assertEquals(self.asset2.get_monikers(), ['test2', 'test2alt'])

    def test_get_color_set(self):
        self.assertTrue(self.asset0.get_color_set().equals(self.colorset0))
        self.assertTrue(self.asset1.get_color_set().equals(self.colorset1))
        self.assertTrue(self.asset2.get_color_set().equals(self.colorset2))

    def test_get_colorvalue(self):
        utxo = MockUTXO(5,[[1,2],[2,3],[3,4]])

        self.assertEquals(self.asset0.get_colorvalue(utxo), 5)
        self.assertEquals(self.asset1.get_colorvalue(utxo), 2)
        self.assertEquals(self.asset2.get_colorvalue(utxo), 4)

        utxo = MockUTXO(5,[[5,2],[6,3],[3,4]])
        self.assertRaises(Exception, self.asset1.get_colorvalue, utxo)

    def test_parse_value(self):
        self.assertEquals(self.asset0.parse_value(1.25), 125000000)
        self.assertEquals(self.asset1.parse_value(2), 20)
        self.assertEquals(self.asset2.parse_value(5), 5)

    def test_format_value(self):
        self.assertEquals(self.asset0.format_value(10000),'0.0001')
        self.assertEquals(self.asset1.format_value(2),'0.2')
        self.assertEquals(self.asset2.format_value(5),'5')

    def test_get_data(self):
        self.assertEquals(self.asset0.get_data(), self.def0)
        self.assertEquals(self.asset1.get_data(), self.def1)
        self.assertEquals(self.asset2.get_data(), self.def2)

    def test_register_asset_definition(self):
        self.assertRaises(Exception, self.adm.register_asset_definition,
                          self.asset1)

    def test_add_asset_definition(self):
        colorset3 = ColorSet(self.colormap, [self.colormap.d[4]])
        def4 = {'monikers': ['test3'], 'color_set': colorset3.get_data()}
        self.adm.add_asset_definition(def4)
        self.assertTrue(self.adm.get_asset_by_moniker('test3').get_color_set()
                        .equals(colorset3))

    def test_all_assets(self):
        reprs = [asset.__repr__() for asset in self.adm.get_all_assets()]
        self.assertTrue(self.asset0.__repr__() in reprs)
        self.assertTrue(self.asset1.__repr__() in reprs)
        self.assertTrue(self.asset2.__repr__() in reprs)

    def test_get_asset_and_address(self):
        ch = self.asset1.get_color_set().get_color_hash()
        addr = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'
        coloraddress = "%s@%s" % (ch, addr)
        asset, address = self.adm.get_asset_and_address(coloraddress)
        self.assertEquals(asset.__repr__(), self.asset1.__repr__())
        self.assertEquals(addr, address)
        asset, address = self.adm.get_asset_and_address(addr)
        self.assertEquals(asset.__repr__(), self.asset0.__repr__())
        self.assertEquals(addr, address)
        self.assertRaises(Exception, self.adm.get_asset_and_address, '0@0')

if __name__ == '__main__':
    unittest.main()
