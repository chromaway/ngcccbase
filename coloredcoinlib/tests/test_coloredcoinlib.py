#!/usr/bin/env python

import unittest

from coloredcoinlib import blockchain
from coloredcoinlib import store
from coloredcoinlib import builder
from coloredcoinlib import colordef
from coloredcoinlib import colordata


class TestColoredCoin(unittest.TestCase):
    def test_coloredcoin(self):
        blockchain_state = blockchain.BlockchainState(
            "http://bitcoinrpc:8oso9n8E1KnTexnKHn16N3tcsGpfEThksK4ojzrkzn3b"
            "@localhost:18332/")

        # FIXME: this should be mocked, or should use test data
        store_conn = store.DataStoreConnection("color.db")

        cdstore = store.ColorDataStore(store_conn.conn)
        metastore = store.ColorMetaStore(store_conn.conn)

        genesis = {
            'txhash':
            'b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e',
            'outindex': 0,
            'height': 46442}

        colordef1 = colordef.OBColorDefinition(1, genesis)

        cdbuilder = builder.FullScanColorDataBuilder(
            cdstore, blockchain_state, colordef1, metastore)

        cdata = colordata.ThickColorData(cdbuilder, blockchain_state, cdstore)
