#!/usr/bin/env python

import unittest

import sqlite3

from ngcccbase import txdb

import txcons # FIXME: will explode if not run from main directory
              #        this is a symptom of dumping stuff in the main
              #        directory, moving txcons into ngcccbase will
              #        resolve this
from coloredcoinlib import txspec

class TestTxDataStoreInitialization(unittest.TestCase):
    def test_initialization(self):
        connection = sqlite3.connect(":memory:")
        store = txdb.TxDataStore(connection)
        self.assertTrue(store.table_exists("tx_data"))
        self.assertTrue(store.table_exists("tx_address"))

class TestTxDataStore(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(":memory:")
        self.store = txdb.TxDataStore(connection)
        self.model = None

    def test_add_empty_signed_tx(self):
        composed = txspec.ComposedTxSpec([], [])
        transaction = txcons.SignedTxSpec(self.model, composed, False)
        self.store.add_signed_tx("FAKEHASH", transaction)

        stored_id, stored_hash, stored_data, stored_status = self.store.get_tx_by_hash("FAKEHASH")

        self.assertEqual(stored_hash, "FAKEHASH")
        self.assertEqual(stored_data, transaction.get_hex_tx_data())
