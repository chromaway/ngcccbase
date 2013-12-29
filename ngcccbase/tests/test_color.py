#!/usr/bin/env python

import os
import unittest

from pycoin.encoding import (a2b_hashed_base58, from_bytes_32,
                             public_pair_to_hash160_sec)
from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint

from ngcccbase.color import ColoredCoinContext


class TestColor(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        c = {
            'ccc': {'colordb_path': self.path},
            'testnet': False,
            }
        self.address = '5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF'
        self.ccc = ColoredCoinContext(c)

    def test_init(self):
        self.assertTrue(self.ccc.colordata)

    def test_raw_to_address(self):
        privkey = from_bytes_32(a2b_hashed_base58(self.address)[1:])
        pubkey = BasePoint * privkey
        raw = public_pair_to_hash160_sec(pubkey.pair(), False)
        addr = self.ccc.raw_to_address(raw)
        self.assertEqual(addr,'1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj')


if __name__ == '__main__':
    unittest.main()
