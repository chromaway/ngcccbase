#!/usr/bin/env python

import unittest

from coloredcoinlib.colordata import (ThickColorData, ThinColorData,
                                      UnfoundTransactionError)
from test_colormap import MockColorMap
from test_txspec import MockTX

from ngcccbase.services.chroma import ChromanodeInterface
from coloredcoinlib import DataStoreConnection
from coloredcoinlib import ColorMetaStore
from coloredcoinlib import AidedColorDataBuilder
from coloredcoinlib import ColorDataStore
from coloredcoinlib import ColorMap
from coloredcoinlib import ColorDataBuilderManager
from coloredcoinlib import store
import sqlite3

class MockBuilder:
    def ensure_scanned_upto(self, i, j):
        return True
    def scan_tx(self, a, b):
        return
    def scan_txhash(self, a, b):
        return
    def get_color_def_map(self, x):
        m = MockColorMap()
        r = {}
        for k,v in m.d.items():
            r[k] = m.get_color_def(v)
            r[k].genesis = {'txhash': '2'}
        return r


class MockBlockchain:
    def get_tx_blockhash(self, h):
        if h == '':
            return '', False
        elif h == '1':
            return 'tmp', True
        elif h == '2' or h == '9':
            return None, True
        else:
            return 'tmp', True
    def get_tx(self, h):
        if h == 'nope':
            return None
        return MockTX(h, [1,1,1], [1,2])
    def get_best_blockhash(self):
        return '7'
    def get_mempool_txs(self):
        return [MockTX('%s' % i, [1,1,1], [1,2]) for i in range(8)]


class MockStore:
    def get_any(self, a, b):
        return [(1, 5, ''), (1, 6, '')]


@unittest.skip("broken")
class TestColorData(unittest.TestCase):

    def setUp(self):
        builder = MockBuilder()
        blockchain = MockBlockchain()
        store = MockStore()
        colormap = MockColorMap()
        self.mock_thick = ThickColorData(builder, blockchain, store, colormap)
        self.mock_thin = ThinColorData(builder, blockchain, store, colormap)

    def test_thick(self):
        self.assertRaises(UnfoundTransactionError, self.mock_thick.get_colorvalues,
                          set([1,2]), '', 0)
        cvs = self.mock_thick.get_colorvalues(set([1,2]), '1', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)
        cvs = self.mock_thick.get_colorvalues(set([1,2]), '2', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)

        self.assertRaises(UnfoundTransactionError, self.mock_thick.get_colorvalues,
                          set([1,2]), '9', 0)

    def test_thin(self):
        self.assertRaises(UnfoundTransactionError, self.mock_thin.get_colorvalues,
                          set([1,2]), 'nope', 0)
        cvs = self.mock_thin.get_colorvalues(set([1,2]), '1', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)
        cvs = self.mock_thin.get_colorvalues(set([1,2]), '2', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)


@unittest.skip("history to long, takes forever")
class TestColorData_OBC(unittest.TestCase):

    def setUp(self):
        wallet_path = "wallets/testnet.wallet_alpha"
        _store_conn = store.DataStoreConnection(wallet_path, True)
        _store_conn.conn.row_factory = sqlite3.Row
        conn = _store_conn.conn
        config = store.PersistentDictStore(conn, "wallet")
        self.blockchain_state = ChromanodeInterface(None, True)
        params = config.get('ccc', {})
        self.store_conn = DataStoreConnection(params.get("colordb_path", 
                                                         "color.db"))
        self.metastore = ColorMetaStore(self.store_conn.conn)
        color_data_builder = AidedColorDataBuilder
        self.cdstore = ColorDataStore(self.store_conn.conn)
        self.colormap = ColorMap(self.metastore)
        cdbuilder = ColorDataBuilderManager(self.colormap,
                                            self.blockchain_state,
                                            self.cdstore,
                                            self.metastore,
                                            color_data_builder)
        self.thin = ThinColorData(cdbuilder, self.blockchain_state,
                                  self.cdstore, self.colormap)

    def test_obc_of_uncolored(self):
            color_id_set = set([16])
            txhash = 'a4c5d76df7872f44ec06c9acb9d0ee80eac8380dd344dae2b2c88bce83a9df75'
            outindex = 1
            cvs = self.thin.get_colorvalues(color_id_set, txhash, outindex)
            print cvs


if __name__ == '__main__':
    unittest.main()
