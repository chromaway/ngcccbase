#!/usr/bin/env python

import copy
import unittest

from pycoin.encoding import EncodingError

from coloredcoinlib import ColorSet
from coloredcoinlib.tests.test_colorset import MockColorMap
from ngcccbase.address import InvalidAddressError
from ngcccbase.asset import AssetDefinition
from ngcccbase.bip0032 import HDWalletAddressManager
from test_deterministic import TestDeterministic


class TestBIP0032(TestDeterministic):

    def setUp(self):
        super(TestBIP0032, self).setUp()
        c = {
            'hdw_master_key': self.master_key,
            'hdwam': {
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
        self.maindwam = HDWalletAddressManager(self.colormap, c)

    def test_init_new_wallet(self):
        c = copy.deepcopy(self.config)
        del c['hdw_master_key']
        del c['hdwam']
        newdwam = HDWalletAddressManager(self.colormap, c)
        params = newdwam.init_new_wallet()
        self.assertNotEqual(self.config['hdw_master_key'],
                            newdwam.config['hdw_master_key'])

        c = copy.deepcopy(self.config)
        c['addresses'][0]['address_data'] = 'notreal'
        self.assertRaises(EncodingError, HDWalletAddressManager,
                          self.colormap, c)



if __name__ == '__main__':
    unittest.main()
