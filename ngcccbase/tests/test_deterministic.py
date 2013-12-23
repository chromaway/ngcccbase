#!/usr/bin/env python

import copy
import unittest

from pycoin.encoding import EncodingError

from coloredcoinlib import ColorSet
from coloredcoinlib.tests.test_colorset import MockColorMap
from ngcccbase.address import InvalidAddressError
from ngcccbase.asset import AssetDefinition
from ngcccbase.deterministic import DWalletAddressManager


class TestDeterministic(unittest.TestCase):

    def setUp(self):
        self.colormap = MockColorMap()
        d = self.colormap.d
        self.colorset0 = ColorSet(self.colormap, [''])
        self.colorset1 = ColorSet(self.colormap, [d[1]])
        self.colorset1alt = ColorSet(self.colormap, [d[1],d[6]])
        self.colorset2 = ColorSet(self.colormap, [d[2]])
        self.colorset3 = ColorSet(self.colormap, [d[3], d[4]])
        self.def1 = {'monikers': ['test1'],
                     'color_set': self.colorset1.get_data(),
                     'unit':10}
        self.asset1 = AssetDefinition(self.colormap, self.def1)
        self.master_key = '265a1a0ad05e82fa321e3f6f6767679df0c68515797e0e4e24be1afc3272ee658ec53cecb683ab76a8377273347161e123fddf5320cbbce8849b0a00557bd12c'
        self.privkey = '5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF'
        self.pubkey = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'
        c = {
            'dw_master_key': self.master_key,
            'dwam': {
                'genesis_color_sets':[self.colorset1.get_data(),
                                      self.colorset2.get_data()],
                'color_set_states':[
                    {'color_set':self.colorset0.get_data(), "max_index":0},
                    {'color_set':self.colorset1.get_data(), "max_index":3},
                    {'color_set':self.colorset2.get_data(), "max_index":2},
                    ],
                },
            'addresses':[{'address_data': self.privkey,
                          'color_set': self.colorset1.get_data(),
                          }],
            'testnet': False,
            }
        self.config = copy.deepcopy(c)
        self.maindwam = DWalletAddressManager(self.colormap, c)

    def test_init_new_wallet(self):
        c = copy.deepcopy(self.config)
        del c['dw_master_key']
        del c['dwam']
        newdwam = DWalletAddressManager(self.colormap, c)
        params = newdwam.init_new_wallet()
        self.assertNotEqual(self.config['dw_master_key'],
                            newdwam.config['dw_master_key'])

        c = copy.deepcopy(self.config)
        c['addresses'][0]['address_data'] = 'notreal'
        self.assertRaises(EncodingError, DWalletAddressManager,
                          self.colormap, c)

    def test_get_new_address(self):
        self.assertEqual(self.maindwam.get_new_address(self.colorset2).index,
                         3)
        self.assertEqual(self.maindwam.get_new_address(self.asset1).index,
                         4)

    def test_get_new_genesis_address(self):
        addr = self.maindwam.get_new_genesis_address()
        self.assertEqual(addr.index, 2)
        addr2 = self.maindwam.get_new_address(addr.get_color_set())
        self.assertEqual(addr2.index, 0)

    def test_get_update_genesis_address(self):
        addr = self.maindwam.get_genesis_address(0)
        self.maindwam.update_genesis_address(addr, self.colorset1alt)
        self.assertEqual(addr.get_color_set(), self.colorset1alt)

    def test_get_change_address(self):
        addr = self.maindwam.get_change_address(self.colorset0)
        self.assertEqual(addr.get_color_set().__repr__(),
                         self.colorset0.__repr__())
        self.assertEqual(self.maindwam.get_change_address(self.colorset3).index,
                         0)

    def test_get_all_addresses(self):
        addrs = [a.get_address() for a in self.maindwam.get_all_addresses()]
        self.assertTrue(self.pubkey in addrs)


if __name__ == '__main__':
    unittest.main()
