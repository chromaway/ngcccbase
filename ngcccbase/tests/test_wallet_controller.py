#!/usr/bin/env python

import unittest

from pycoin.tx.script import opcodes, tools

from coloredcoinlib import ColorSet, InvalidColorDefinitionError
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController, AssetMismatchError


class MockBitcoinD(object):
    def __init__(self, txhash):
        self.txhash = txhash
    def sendrawtransaction(self, x):
        return self.txhash
    def getblockcount(self):
        return 1
    def getrawmempool(self):
        return [self.txhash]
    def getrawtransaction(self, t, n):
        return "0100000002f7876bd7227065771c233686c9734c0470905d55c41441241eab1ba35b5ae44f000000008b483045022100e75c071563c902d021575736209caed88f86817bc1f4f8873bdfee0b00770d64022055d1bacdc16e848c202bf429861de4d853bc3d7a7cc9a8cd71741c20373df4ef01410473930d05b479dc75d8b9ae78663b8685bf3913509d8084b5d0ab24876d740c2c790c1c6050fb78e2c0694ea2604c6529d7dcb48384d8516e582e212d2be713cffffffffff7876bd7227065771c233686c9734c0470905d55c41441241eab1ba35b5ae44f010000008b48304502204200e814121376535732a71fd3afb7613fb09c079289fbfaa47ac4510c11d36c022100a72a6be63f2eb8a6ce62df4df3c3415723e709b4280dc1504c9a123af48f624801410473930d05b479dc75d8b9ae78663b8685bf3913509d8084b5d0ab24876d740c2c790c1c6050fb78e2c0694ea2604c6529d7dcb48384d8516e582e212d2be713cfffffffff0210270000000000001976a914c6add3894dbedcd535f13aa60ef6abbcf05b68b188ac447c9a3b000000001976a914ed2b08274a56573e9af0114822a5e867609b7fa288ac00000000"
    def getblock(self, t):
        return {'blockhash': self.getblockhash(''), 'tx': '', 'height': 1, 'previousblockhash': 'coinbase'}
    def getblockhash(self, h):
        return "11111111111111111111111111111111"


class TestWalletController(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.config = {'dw_master_key': 'test', 'testnet': True, 'ccc': {
                'colordb_path' : self.path
                }, 'bip0032': False }
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.wc = WalletController(self.model)
        self.wc.testing = True
        self.wc.debug = True
        self.colormap = self.model.get_color_map()
        self.bcolorset = ColorSet(self.colormap, [''])
        wam = self.model.get_address_manager()
        self.baddress = wam.get_new_address(self.bcolorset)
        self.baddr = self.baddress.get_address()

        self.blockhash = '00000000c927c5d0ee1ca362f912f83c462f644e695337ce3731b9f7c5d1ca8c'
        self.txhash = '4fe45a5ba31bab1e244114c4555d9070044c73c98636231c77657022d76b87f7'

        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.baddress.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.baddr, self.txhash,
                                           0, 100, script)

        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.baddress.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.baddr, self.txhash,
                                           1, 1000000000, script)

        self.model.ccc.blockchain_state.bitcoind = MockBitcoinD('test')
        def x(s):
            return self.blockhash, True
        self.model.ccc.blockchain_state.get_tx_blockhash = x
        self.moniker = 'test'
        self.wc.issue_coins(self.moniker, 'obc', 10000, 1)
        self.asset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker(self.moniker)
        self.basset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker('bitcoin')
        self.color_id = list(self.asset.color_set.color_id_set)[0]
        self.model.ccc.metastore.set_as_scanned(self.color_id, self.blockhash)

    def test_issue(self):
        self.assertRaises(InvalidColorDefinitionError, self.wc.issue_coins,
                          self.moniker, 'nonexistent', 10000, 1)
        item = self.wc.get_history(self.asset)[0]
        self.assertEqual(item['action'], 'issued')
        self.assertEqual(item['value'], 10000)
        self.wc.scan_utxos()
        item = self.wc.get_history(self.asset)[0]
        self.assertEqual(item['action'], 'issued')
        self.assertEqual(item['value'], 10000)

    def test_new_address(self):
        addr = self.wc.get_new_address(self.asset)
        addrs = self.wc.get_all_addresses(self.asset)
        self.assertEqual(len(addr.get_address()), 34)
        self.assertTrue(addr in addrs)
        for d in self.wc.get_address_balance(self.asset):
            if d['address'] == addr.get_address():
                self.assertEqual(d['value'], 0)

    def test_get_all_assets(self):
        self.assertTrue(self.asset in self.wc.get_all_assets())

    def test_get_balance(self):
        self.assertEqual(self.wc.get_balance(self.asset), 10000)

    def test_add_asset(self):
        moniker = 'addtest'
        params = {"monikers": [moniker],
                  "color_set": ['obc:aaaaaaaaaaaaaaaaa:0:0'], "unit": 1}
        self.wc.add_asset_definition(params)
        asset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker(moniker)
        
        self.assertEqual(self.wc.get_balance(asset), 0)
        self.assertEqual(self.wc.get_history(asset), [])

    def test_send(self):
        addr1 = self.wc.get_new_address(self.asset)
        addr2 = self.wc.get_new_address(self.asset)
        color_addrs = [addr1.get_color_address(), addr2.get_color_address()]
        self.wc.send_coins(self.asset, color_addrs, [1000, 2000])
        self.assertRaises(AssetMismatchError, self.wc.send_coins, self.basset,
                          color_addrs, [1000, 2000])


if __name__ == '__main__':
    unittest.main()
