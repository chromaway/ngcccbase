#!/usr/bin/env python

import unittest

import sqlite3

from ngcccbase import txdb, txcons, utxodb
from ngcccbase.address import LooseAddressRecord
from ngcccbase.services.electrum import (ElectrumInterface,
                                         EnhancedBlockchainState)
from ngcccbase.txdb import (TX_STATUS_UNKNOWN, TX_STATUS_UNCONFIRMED,
                            TX_STATUS_CONFIRMED, TX_STATUS_INVALID)
from coloredcoinlib import txspec

from pycoin.tx.script import tools


class TestTxDataStoreInitialization(unittest.TestCase):
    def test_initialization(self):
        connection = sqlite3.connect(":memory:")
        store = txdb.TxDataStore(connection)
        self.assertTrue(store.table_exists("tx_data"))


class MockConn(object):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")

class MockModel(object):
    def __init__(self):
        self.store_conn = MockConn()

    def is_testnet(self):
        return False
    def get_blockchain_state(self):
        server_url = "electrum.pdmc.net"
        ei = ElectrumInterface(server_url, 50001)
        return EnhancedBlockchainState(server_url, 50001)


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

    def test_add_tx(self):
        txhash = "FAKEHASH"
        transaction, address = fake_transaction(self.model)
        txdata = transaction.get_hex_tx_data()
        self.store.add_tx(txhash, txdata)

        stored_id, stored_hash, stored_data, stored_status = \
            self.store.get_tx_by_hash(txhash)

        self.assertEqual(stored_hash, txhash)
        self.assertEqual(stored_data, transaction.get_hex_tx_data())

        self.assertEqual(stored_status, TX_STATUS_UNKNOWN)
        self.store.set_tx_status(txhash, TX_STATUS_CONFIRMED)
        self.assertEqual(self.store.get_tx_status(txhash), TX_STATUS_CONFIRMED)
        self.store.purge_tx_data()
        self.assertEqual(self.store.get_tx_by_hash(txhash), None)


class TestVerifiedTxDb(unittest.TestCase):
    def setUp(self):
        self.model = MockModel()
        self.txdb = txdb.VerifiedTxDb(MockModel(), {})

    def test_identify_tx_status(self):
        status = self.txdb.identify_tx_status(
            'b1c68049c1349399fb867266fa146a854c16cd8a18a01d3cd7921ab9d5af1a8b')
        self.assertEqual(status, TX_STATUS_CONFIRMED)
        status = self.txdb.identify_tx_status(
            'b1c68049c1349399fb867266fa146a854c16cd8a18a01d3cd7921ab9d5af1a8b')
        self.assertEqual(status, TX_STATUS_CONFIRMED)
        status = self.txdb.identify_tx_status(
            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
        self.assertEqual(status, TX_STATUS_INVALID)


if __name__ == '__main__':
    unittest.main()
