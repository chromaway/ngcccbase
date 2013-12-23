#!/usr/bin/env python

import datetime
import unittest

from coloredcoinlib.blockchain import BlockchainState
from coloredcoinlib.builder import (ColorDataBuilderManager,
                                    FullScanColorDataBuilder, AidedColorDataBuilder)
from coloredcoinlib.colordata import ThickColorData, ThinColorData
from coloredcoinlib.colormap import ColorMap
from coloredcoinlib.store import DataStoreConnection, ColorDataStore, ColorMetaStore


class TestAided(unittest.TestCase):

    def makeBuilder(self):
        self.cdbuilder = ColorDataBuilderManager(self.colormap,
                                                 self.blockchain_state,
                                                 self.cdstore,
                                                 self.metastore,
                                                 AidedColorDataBuilder)
        self.colordata = ThinColorData(self.cdbuilder,
                                       self.blockchain_state,
                                       self.cdstore,
                                       self.colormap)

    def setUp(self):
        self.blockchain_state = BlockchainState.from_url(None, True)
        self.store_conn = DataStoreConnection(":memory:")
        self.cdstore = ColorDataStore(self.store_conn.conn)
        self.metastore = ColorMetaStore(self.store_conn.conn)
        self.colormap = ColorMap(self.metastore)
        self.makeBuilder()
        self.blue_desc = "obc:" \
            "b1586cd10b32f78795b86e9a3febe58d" \
            "cb59189175fad884a7f4a6623b77486e" \
            ":0:46442"
        self.red_desc = "obc:" \
            "8f6c8751f39357cd42af97a67301127d" \
            "497597ae699ad0670b4f649bd9e39abf" \
            ":0:46444"
        self.blue_id = self.colormap.resolve_color_desc(self.blue_desc)
        self.red_id = self.colormap.resolve_color_desc(self.red_desc)
        self.bh = "00000000152164fcc3589ef36a0c34c1c821676e5766787a2784a761dd3dbfb5"
        self.bh2 = "0000000001167e13336f386acbc0d9169dd929ecb1e5d44229fc870206e669f8"
        self.bh3 = "0000000002fda52e8ad950d48651b3a86bce6d80eb016dffbec5477f10467541"
    def test_get_color_def_map(self):
        cdm = self.cdbuilder.get_color_def_map(set([self.blue_id,
                                                    self.red_id]))
        self.assertTrue(self.blue_id in cdm.keys())
        self.assertTrue(self.red_id in cdm.keys())

    def test_zero_scan(self):
        color_id_set = set([0])
        self.cdbuilder.ensure_scanned_upto(color_id_set, '')
        self.cdbuilder.scan_tx(color_id_set, '')

    def test_scan_txhash(self):
        # builder
        builder = self.cdbuilder.get_builder(self.blue_id)
        if not builder.metastore.did_scan(self.blue_id, self.bh):
            builder.ensure_scanned_upto(self.bh)
            self.assertTrue(builder.metastore.did_scan(self.blue_id, self.bh))

        # test scans
        blue_set = set([self.blue_id])
        red_set = set([self.red_id])
        br_set = blue_set | red_set
        tx = "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e"
        self.cdbuilder.scan_txhash(blue_set, tx)
        self.assertTrue(self.cdbuilder.cdstore.get(self.blue_id, tx, 0))
        tx = "f50f29906ce306be3fc06df74cc6a4ee151053c2621af8f449b9f62d86cf0647"
        self.cdbuilder.scan_txhash(blue_set, tx)
        self.assertTrue(self.cdbuilder.cdstore.get(self.blue_id, tx, 0))
        tx = "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf" 
        self.cdbuilder.scan_txhash(blue_set, tx)
        self.assertFalse(self.cdbuilder.cdstore.get(self.blue_id, tx, 0))

    def test_scan_blockchain(self):
        builder = self.cdbuilder.get_builder(self.blue_id)
        builder.scan_blockchain([self.bh2, self.bh2])

    def test_sanity(self):
        blue_set = set([self.blue_id])
        red_set = set([self.red_id])
        br_set = blue_set | red_set
        label = {self.blue_id:'Blue', self.red_id:'Red'}

        g = self.colordata.get_colorvalues

        cv = g(
            br_set,
            "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e",
            0)[0]
        
        self.assertEqual(cv.get_color_id(), self.blue_id)
        self.assertEqual(cv.get_value(), 1000)


        cv = g(
            br_set,
            "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf",
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 1000)

        cvs = g(
            br_set,
            "b1586cd10b32f78795b86e9a3febe58dcb59189175fad884a7f4a6623b77486e",
            1)
        self.assertEqual(len(cvs), 0)

        cvs = g(
            br_set,
            "8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf",
            1)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            'c1d8d2fb75da30b7b61e109e70599c0187906e7610fe6b12c58eecc3062d1da5',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 500)
        
        cv = g(
            br_set,
            '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 150)

        cvs = g(
            br_set,
            '3a60b70d425405f3e45f9ed93c30ca62b2a97e692f305836af38a524997dd01d',
            0)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            '8f6c8751f39357cd42af97a67301127d497597ae699ad0670b4f649bd9e39abf',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)
        self.assertEqual(cv.get_value(), 1000)

        cv = g(
            br_set,
            'f50f29906ce306be3fc06df74cc6a4ee151053c2621af8f449b9f62d86cf0647',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.blue_id)
        self.assertEqual(cv.get_value(), 500)


        self.cdbuilder.scan_txhash(blue_set, '7e40d2f414558be60481cbb976e78f2589bc6a9f04f38836c18ed3d10510dce5')

        cv = g(
            br_set,
            '7e40d2f414558be60481cbb976e78f2589bc6a9f04f38836c18ed3d10510dce5',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.blue_id)
        self.assertEqual(cv.get_value(), 100)

        cv = g(
            br_set,
            '4b60bb49734d6e26d798d685f76a409a5360aeddfddcb48102a7c7ec07243498',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)

        cvs = g(
            br_set,
            '342f119db7f9989f594d0f27e37bb5d652a3093f170de928b9ab7eed410f0bd1',
            0)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            'bd34141daf5138f62723009666b013e2682ac75a4264f088e75dbd6083fa2dba',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.blue_id)

        cvs = g(
            br_set,
            'bd34141daf5138f62723009666b013e2682ac75a4264f088e75dbd6083fa2dba',
            1)
        self.assertEqual(len(cvs), 0)

        cv = g(
            br_set,
            '36af9510f65204ec5532ee62d3785584dc42a964013f4d40cfb8b94d27b30aa1',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)

        cv = g(
            br_set,
            '741a53bf925510b67dc0d69f33eb2ad92e0a284a3172d4e82e2a145707935b3e',
            0)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)

        cv = g(
            br_set,
            '741a53bf925510b67dc0d69f33eb2ad92e0a284a3172d4e82e2a145707935b3e',
            1)[0]
        self.assertEqual(cv.get_color_id(), self.red_id)


class TestFullScan(TestAided):

    def makeBuilder(self):
        self.cdbuilder = ColorDataBuilderManager(self.colormap,
                                                 self.blockchain_state,
                                                 self.cdstore,
                                                 self.metastore,
                                                 FullScanColorDataBuilder)
        self.colordata = ThickColorData(self.cdbuilder,
                                        self.blockchain_state,
                                        self.cdstore,
                                        self.colormap)


if __name__ == '__main__':
    unittest.main()
