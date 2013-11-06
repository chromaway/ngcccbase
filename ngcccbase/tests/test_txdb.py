#!/usr/bin/env python

import unittest

import sqlite3

from ngcccbase import txdb

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

    def test_store(self):
        pass
