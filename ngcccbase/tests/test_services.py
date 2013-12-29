#!/usr/bin/env python

import unittest

from ngcccbase.services.blockchain import BlockchainInfoInterface, AbeInterface
from ngcccbase.services.electrum import (ConnectionError,
                                         ElectrumInterface, EnhancedBlockchainState)


class TestElectrum(unittest.TestCase):

    def setUp(self):
        self.server_url = "electrum.cafebitcoin.com"
        self.ei = ElectrumInterface(self.server_url, 50001)
        self.bcs = EnhancedBlockchainState(self.server_url, 50001)
        self.txhash = 'b1c68049c1349399fb867266fa146a854c16cd8a18a01d3cd7921ab9d5af1a8b'
        self.height = 277287
        self.raw_tx = '01000000010000000000000000000000000000000000000000000000000000000000000000ffffffff4803273b04062f503253482f049fe1bd5208ee5f364f06648bae2e522cfabe6d6de0a3e574e400f64403ea10de4ff3bc0dcb42d49549e273a9faa4eac33b04734804000000000000000000000001cde08d95000000001976a91480ad90d403581fa3bf46086a91b2d9d4125db6c188ac00000000'
        self.address = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'

    def test_connect(self):
        self.assertRaises(ConnectionError, ElectrumInterface, 'cnn.com', 50001)

    def test_get_utxo(self):
        self.assertEqual(self.ei.get_utxo(self.address), [])

    def test_get_version(self):
        self.assertTrue(float(self.ei.get_version()) >= 0.8)

    def test_get_raw_transaction(self):
        self.assertEqual(self.ei.get_raw_transaction(self.txhash, self.height),
                         self.raw_tx)

        self.assertEqual(self.bcs.get_raw_transaction(self.txhash), self.raw_tx)

    def test_get_height(self):
        self.assertEqual(self.bcs.get_tx_block_height(self.txhash)[0], self.height)

    def test_get_tx(self):
        self.assertEqual(self.bcs.get_tx(self.txhash).hash, self.txhash)


class TestBlockchain(unittest.TestCase):
    def setUp(self):
        self.address = '13ph5zPCBLeZcPph9FBZKeeyDjvU2tvcMY'
        self.txhash = 'd7b9a9da6becbf47494c27e913241e5a2b85c5cceba4b2f0d8305e0a87b92d98'
        self.address2 = '1CC3X2gu58d6wXUWMffpuzN9JAfTUWu4Kj'

    def test_blockchain(self):
        self.assertEqual(BlockchainInfoInterface.get_utxo(self.address)[0][0],
                         self.txhash)
        self.assertEqual(BlockchainInfoInterface.get_utxo(self.address2), [])


if __name__ == '__main__':
    unittest.main()
