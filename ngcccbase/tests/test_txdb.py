#!/usr/bin/env python

import unittest

import sqlite3

from ngcccbase import txdb, txcons, utxodb
from ngcccbase.address import LooseAddressRecord
from coloredcoinlib import txspec

from pycoin.tx.script import tools


class TestTxDataStoreInitialization(unittest.TestCase):
    def test_initialization(self):
        connection = sqlite3.connect(":memory:")
        store = txdb.TxDataStore(connection)
        self.assertTrue(store.table_exists("tx_data"))
        self.assertTrue(store.table_exists("tx_address"))


class MockModel(object):
    def is_testnet(self):
        return False


def fake_transaction(model=MockModel()):
    key = "5Kb8kLf9zgWQnogidDA76MzPL6TsZZY36hWXMssSzNydYXYB9KF"

    address = LooseAddressRecord(address_data=key)
    script = tools.compile(
        "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
            address.rawPubkey().encode("hex"))).encode("hex")

    txin = utxodb.UTXO("D34DB33F", 0, 1, script)
    txin.address_rec = address
    txout = txspec.ComposedTxSpec.TxOut(1, address.get_address())
    composed = txspec.ComposedTxSpec([txin], [txout])
    return txcons.RawTxSpec.from_composed_tx_spec(model, composed), address


class TestTxDataStore(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(":memory:")
        self.store = txdb.TxDataStore(connection)
        self.model = MockModel()

    def test_empty_signed_tx(self):
        txhash = "FAKEHASH"
        transaction, address = fake_transaction(self.model)
        self.store.add_signed_tx(txhash, transaction)

        stored_id, stored_hash, stored_data, stored_status = \
            self.store.get_tx_by_hash(txhash)

        self.assertEqual(stored_hash, txhash)
        self.assertEqual(stored_data, transaction.get_hex_tx_data())

    def test_signed_tx(self):
        txhash = "FAKEHASH"
        transaction, address = fake_transaction(self.model)
        self.store.add_signed_tx(txhash, transaction)

        txes = self.store.get_tx_by_output_address(address.get_address())
        stored_hash, stored_data, stored_status = txes.fetchone()

        self.assertEqual(stored_hash, txhash)
        self.assertEqual(stored_data, transaction.get_hex_tx_data())


if __name__ == '__main__':
    unittest.main()
