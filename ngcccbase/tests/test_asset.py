#!/usr/bin/env python

import unittest

from coloredcoinlib import OBColorDefinition, ColorSet, SimpleColorValue, IncompatibleTypesError
from coloredcoinlib.tests.test_colorset import MockColorMap
from coloredcoinlib.tests.test_txspec import MockUTXO

from ngcccbase.asset import (AssetDefinition, AdditiveAssetValue,
                             AssetTarget, AssetDefinitionManager)


class TestAssetDefinition(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [''])
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

        self.assetvalue0 = AdditiveAssetValue(asset=self.asset0, value=5)
        self.assetvalue1 = AdditiveAssetValue(asset=self.asset0, value=6)
        self.assetvalue2 = AdditiveAssetValue(asset=self.asset1, value=7)

        self.assettarget0 = AssetTarget('address0', self.assetvalue0)
        self.assettarget1 = AssetTarget('address1', self.assetvalue1)
        self.assettarget2 = AssetTarget('address2', self.assetvalue2)

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
        g = {'txhash':'blah', 'height':1, 'outindex':0}
        cid0 = list(self.colorset0.color_id_set)[0]
        cdef0 = OBColorDefinition(cid0, g)
        cid1 = list(self.colorset1.color_id_set)[0]
        cdef1 = OBColorDefinition(cid1, g)
        cid2 = list(self.colorset2.color_id_set)[0]
        cdef2 = OBColorDefinition(cid2, g)
        cv0 = SimpleColorValue(colordef=cdef0, value=1)
        cv1 = SimpleColorValue(colordef=cdef1, value=2)
        cv2 = SimpleColorValue(colordef=cdef2, value=3)

        utxo = MockUTXO([cv0, cv1, cv2])

        self.assertEquals(self.asset0.get_colorvalue(utxo), cv0)
        self.assertEquals(self.asset1.get_colorvalue(utxo), cv1)
        self.assertEquals(self.asset2.get_colorvalue(utxo), cv2)

        utxo = MockUTXO([cv0, cv2])
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

    def test_add(self):
        assetvalue3 = self.assetvalue0 + self.assetvalue1
        self.assertEqual(assetvalue3.get_value(), 11)
        assetvalue3 = 0 + self.assetvalue1
        self.assertEqual(assetvalue3.get_value(), 6)
        self.assertRaises(IncompatibleTypesError, self.assetvalue0.__add__,
                          self.assetvalue2)

    def test_iadd(self):
        assetvalue = self.assetvalue0.clone()
        assetvalue += self.assetvalue1
        self.assertEqual(assetvalue.get_value(), 11)

    def test_sub(self):
        assetvalue = self.assetvalue1 - self.assetvalue0
        self.assertEqual(assetvalue.get_value(), 1)
        assetvalue = self.assetvalue1 - 0
        self.assertEqual(assetvalue.get_value(), self.assetvalue1.get_value())

    def test_lt(self):
        self.assertTrue(self.assetvalue0 < self.assetvalue1)
        self.assertTrue(self.assetvalue1 > self.assetvalue0)
        self.assertTrue(self.assetvalue1 >= self.assetvalue0)
        self.assertTrue(self.assetvalue1 > 0)

    def test_sum(self):
        assetvalues = [self.assetvalue0, self.assetvalue1,
                       AdditiveAssetValue(asset=self.asset0, value=3)]
        self.assertEqual(AdditiveAssetValue.sum(assetvalues).get_value(), 14)

    def test_get_asset(self):
        self.assertEqual(self.assettarget0.get_asset(), self.asset0)

    def test_get_value(self):
        self.assertEqual(self.assettarget0.get_value(), self.assetvalue0.get_value())

    def test_sum(self):
        assettargets = [self.assettarget0, self.assettarget1,
                        AssetTarget('address3',self.assettarget1)]
        self.assertEqual(AssetTarget.sum(assettargets).get_value(), 17)
        self.assertEqual(AssetTarget.sum([]), 0)

    def test_get_address(self):
        self.assertEqual(self.assettarget0.get_address(), 'address0')

    def test_repr(self):
        self.assertEqual(self.assettarget0.__repr__(), 'address0: Asset Value: 5')


if __name__ == '__main__':
    unittest.main()
