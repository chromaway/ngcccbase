#!/usr/bin/env python

import unittest

from bitcoin.rpc import RawProxy

from coloredcoinlib.blockchain import BlockchainState, script_to_raw_address


class TestBlockchainState(unittest.TestCase):
    def setUp(self):
        self.bs = BlockchainState.from_url(None, True)
        self.blockhash = '00000000c927c5d0ee1ca362f912f83c462f644e695337ce3731b9f7c5d1ca8c'
        self.previous_blockhash = '000000000001c503d2e3bff1d73eb53213a8d784206a233181ea11f95c5fd097'
        self.txhash = '72386db4bf4ced6380763d3eb09b634771ba519e200b57da765def26219ef508'
        self.height = 154327
        self.coinbase = '4fe45a5ba31bab1e244114c4555d9070044c73c98636231c77657022d76b87f7'
        self.tx = self.bs.get_tx(self.txhash)
        self.coinbasetx = self.bs.get_tx(self.coinbase)

    def test_get_tx(self):
        self.assertEqual(self.tx.inputs[0].get_txhash()[::-1].encode('hex'), 'c6dcb546bfe4e096e2c2e894fb8c95e9615e6df3095db0e59a4f2413e17a76af')
        self.assertEqual(self.tx.inputs[0].get_outpoint()[1], 1)
        self.assertEqual(self.coinbasetx.inputs[0].get_txhash(), 'coinbase')

    def test_script_to_raw_address(self):
        self.assertEqual(script_to_raw_address(''), None)

    def test_get_block_height(self):
        self.assertEqual(self.bs.get_block_height(self.blockhash), self.height)

    def test_get_blockhash_at_height(self):
        self.assertEqual(self.bs.get_blockhash_at_height(self.height),
                         self.blockhash)

    def test_get_tx_blockhash(self):
        self.assertEqual(self.bs.get_tx_blockhash(self.txhash),
                         (self.blockhash, True))
        self.assertEqual(self.bs.get_tx_blockhash(self.txhash[:-1] + '0'),
                         (None, False))

    def test_get_previous_blockinfo(self):
        self.assertEqual(self.bs.get_previous_blockinfo(self.blockhash)[0],
                         self.previous_blockhash)
        
    def test_ensure(self):
        self.tx.ensure_input_values()
        self.assertTrue(self.tx.have_input_values)
        self.tx.ensure_input_values()
        self.assertTrue(self.tx.have_input_values)
        self.coinbasetx.ensure_input_values()
        self.assertTrue(self.coinbasetx.have_input_values)

    def test_get_best(self):
        self.assertTrue(self.bs.get_best_blockhash())
        
    def test_iter_block_txs(self):
        i = 0
        txs = []
        for tx in self.bs.iter_block_txs(self.blockhash):
            i += 1
            tx.ensure_input_values()
            txs.append(tx.hash)
        self.assertEqual(i, 12)
        sorted_txs = [tx.hash for tx in self.bs.sort_txs(txs)]
        self.assertEqual(len(sorted_txs), 12)
        # a should be before b
        a = '5e9762b340e2f72a66dabe16d738a8ae89d71843286e7c9354eaf299d906845c'
        b = '264b174948d0be47d7661b60ecc88b575ab1216617f5298a230c27f7a34f2e40'
        self.assertTrue(a in sorted_txs)
        self.assertTrue(b in sorted_txs)
        self.assertTrue(sorted_txs.index(a) < sorted_txs.index(b))

    def test_mempool(self):
        mempool_txs = self.bs.get_mempool_txs()
        if len(mempool_txs):
            tx = mempool_txs[0]
            bh = self.bs.get_tx_blockhash(tx.hash)
            self.assertTrue(bh)


if __name__ == '__main__':
    unittest.main()
