#!/usr/bin/env python

import unittest

from coloredcoinlib.colordata import (ThickColorData, ThinColorData,
                                      UnfoundTransactionError)
from test_colormap import MockColorMap
from test_txspec import MockTX


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


class TestColorData(unittest.TestCase):

    def setUp(self):
        builder = MockBuilder()
        blockchain = MockBlockchain()
        store = MockStore()
        colormap = MockColorMap()
        self.thick = ThickColorData(builder, blockchain, store, colormap)
        self.thin = ThinColorData(builder, blockchain, store, colormap)

    def test_thick(self):
        self.assertRaises(UnfoundTransactionError, self.thick.get_colorvalues,
                          set([1,2]), '', 0)
        cvs = self.thick.get_colorvalues(set([1,2]), '1', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)
        cvs = self.thick.get_colorvalues(set([1,2]), '2', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)

        self.assertRaises(UnfoundTransactionError, self.thick.get_colorvalues,
                          set([1,2]), '9', 0)

    def test_thin(self):
        self.assertRaises(UnfoundTransactionError, self.thin.get_colorvalues,
                          set([1,2]), 'nope', 0)
        cvs = self.thin.get_colorvalues(set([1,2]), '1', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)
        cvs = self.thin.get_colorvalues(set([1,2]), '2', 0)
        self.assertEquals(cvs[0].get_value(), 5)
        self.assertEquals(cvs[1].get_value(), 6)


if __name__ == '__main__':
    unittest.main()
