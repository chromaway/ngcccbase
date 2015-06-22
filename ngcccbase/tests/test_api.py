#!/usr/bin/env python


import os
import unittest
import json
import tempfile
from ngcccbase.api import Ngccc
from ngcccbase import sanitize


fixtures = json.load(open("ngcccbase/tests/fixtures.json"))


class AbsTest(object):

    def setUp(self):

        # read only unit test wallet
        ro_wallet_path = "ngcccbase/tests/ro_unittest.wallet"
        self.ro_api = Ngccc(wallet=ro_wallet_path, testnet=True,
                            use_naivetxdb=True)

        # set to True to test bitcoind
        #self.ro_api.setconfigval('use_bitcoind', False)

        # read write unit test wallet
        rw_wallet_path = "ngcccbase/tests/rw_unittest.wallet"
        self.rw_api = Ngccc(wallet=rw_wallet_path, testnet=True,
                            use_naivetxdb=True)

        # set to True to test bitcoind
        #self.rw_api.setconfigval('use_bitcoind', False)

    def tearDown(self):
        # cleanup
        del self.ro_api
        del self.rw_api

        # print running threads
        """
        print ""
        print "BEGIN PRINT RUNNING THREADS"
        print ""
        import sys
        import threading
        import traceback
        for th in threading.enumerate():
            print th
            traceback.print_stack(sys._current_frames()[th.ident])
            print ""
        print ""
        print "END PRINT RUNNING THREADS"
        print ""
        """


class TestHistory(AbsTest, unittest.TestCase):

    def test_uncolored(self):  # FIXME why an empty list?
        moniker = fixtures["history"]["uncolored"]["moniker"]
        expected = fixtures["history"]["uncolored"]["expected"]
        output = self.ro_api.history(moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["history"]["epobc"]["moniker"]
        expected = fixtures["history"]["epobc"]["expected"]
        output = self.ro_api.history(moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["history"]["obc"]["moniker"]
        expected = fixtures["history"]["obc"]["expected"]
        output = self.ro_api.history(moniker)
        self.assertEquals(output, expected)


class TestListAssets(AbsTest, unittest.TestCase):

    def test(self):
        expected = fixtures["listassets"]["expected"]
        output = self.ro_api.listassets()
        self.assertEquals(output, expected)


class TestDumpPrivateKey(AbsTest, unittest.TestCase):

    def test_uncolored(self):
        moniker = fixtures["dumpprivkey"]["uncolored"]["moniker"]
        address = fixtures["dumpprivkey"]["uncolored"]["address"]
        expected = fixtures["dumpprivkey"]["uncolored"]["expected"]
        output = self.ro_api.dumpprivkey(moniker, address)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["dumpprivkey"]["epobc"]["moniker"]
        address = fixtures["dumpprivkey"]["epobc"]["address"]
        expected = fixtures["dumpprivkey"]["epobc"]["expected"]
        output = self.ro_api.dumpprivkey(moniker, address)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["dumpprivkey"]["obc"]["moniker"]
        address = fixtures["dumpprivkey"]["obc"]["address"]
        expected = fixtures["dumpprivkey"]["obc"]["expected"]
        output = self.ro_api.dumpprivkey(moniker, address)
        self.assertEquals(output, expected)


class TestDumpPrivateKeys(AbsTest, unittest.TestCase):

    def test_uncolored(self):
        moniker = fixtures["dumpprivkeys"]["uncolored"]["moniker"]
        expected = fixtures["dumpprivkeys"]["uncolored"]["expected"]
        output = self.ro_api.dumpprivkeys(moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["dumpprivkeys"]["epobc"]["moniker"]
        expected = fixtures["dumpprivkeys"]["epobc"]["expected"]
        output = self.ro_api.dumpprivkeys(moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["dumpprivkeys"]["obc"]["moniker"]
        expected = fixtures["dumpprivkeys"]["obc"]["expected"]
        output = self.ro_api.dumpprivkeys(moniker)
        self.assertEquals(output, expected)


class TestTxOutValue(AbsTest, unittest.TestCase):  # TODO test non wallet tx

    def test_uncolored(self):
        txid = fixtures["txoutvalue"]["uncolored"]["txid"]
        outindex = fixtures["txoutvalue"]["uncolored"]["outindex"]
        moniker = fixtures["txoutvalue"]["uncolored"]["moniker"]
        expected = fixtures["txoutvalue"]["uncolored"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        txid = fixtures["txoutvalue"]["epobc"]["txid"]
        outindex = fixtures["txoutvalue"]["epobc"]["outindex"]
        moniker = fixtures["txoutvalue"]["epobc"]["moniker"]
        expected = fixtures["txoutvalue"]["epobc"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        txid = fixtures["txoutvalue"]["obc"]["txid"]
        outindex = fixtures["txoutvalue"]["obc"]["outindex"]
        moniker = fixtures["txoutvalue"]["obc"]["moniker"]
        expected = fixtures["txoutvalue"]["obc"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)


class TestTxOutValues(AbsTest, unittest.TestCase):  # TODO test non wallet tx

    def test_uncolored(self):
        txid = fixtures["txoutvalues"]["uncolored"]["txid"]
        outindex = fixtures["txoutvalues"]["uncolored"]["outindex"]
        expected = fixtures["txoutvalues"]["uncolored"]["expected"]
        output = self.ro_api.txoutvalues(txid, outindex)
        self.assertEquals(output, expected)

    def test_epobc(self):
        txid = fixtures["txoutvalues"]["epobc"]["txid"]
        outindex = fixtures["txoutvalues"]["epobc"]["outindex"]
        expected = fixtures["txoutvalues"]["epobc"]["expected"]
        output = self.ro_api.txoutvalues(txid, outindex)
        self.assertEquals(output, expected)

    def test_obc(self):
        txid = fixtures["txoutvalues"]["obc"]["txid"]
        outindex = fixtures["txoutvalues"]["obc"]["outindex"]
        expected = fixtures["txoutvalues"]["obc"]["expected"]
        output = self.ro_api.txoutvalues(txid, outindex)
        self.assertEquals(output, expected)


class TestGetUTXOs(AbsTest, unittest.TestCase):

    def test_uncolored(self):
        moniker = fixtures["getutxos"]["uncolored"]["moniker"]
        amount = fixtures["getutxos"]["uncolored"]["amount"]
        expected = fixtures["getutxos"]["uncolored"]["expected"]
        output = self.ro_api.getutxos(moniker, amount)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["getutxos"]["epobc"]["moniker"]
        amount = fixtures["getutxos"]["epobc"]["amount"]
        expected = fixtures["getutxos"]["epobc"]["expected"]
        output = self.ro_api.getutxos(moniker, amount)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["getutxos"]["obc"]["moniker"]
        amount = fixtures["getutxos"]["obc"]["amount"]
        expected = fixtures["getutxos"]["obc"]["expected"]
        output = self.ro_api.getutxos(moniker, amount)
        self.assertEquals(output, expected)

    def test_undefined(self):
        def callback():
            moniker = fixtures["getutxos"]["undefined"]["moniker"]
            amount = fixtures["getutxos"]["undefined"]["amount"]
            self.ro_api.getutxos(moniker, amount)
        self.assertRaises(sanitize.AssetNotFound, callback)


class TestReceived(AbsTest, unittest.TestCase):

    def test_uncolored(self):
        moniker = fixtures["received"]["uncolored"]["moniker"]
        expected = fixtures["received"]["uncolored"]["expected"]
        output = self.ro_api.received(moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["received"]["epobc"]["moniker"]
        expected = fixtures["received"]["epobc"]["expected"]
        output = self.ro_api.received(moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["received"]["obc"]["moniker"]
        expected = fixtures["received"]["obc"]["expected"]
        output = self.ro_api.received(moniker)
        self.assertEquals(output, expected)

    def test_undefined(self):
        def callback():
            moniker = fixtures["received"]["undefined"]["moniker"]
            self.ro_api.received(moniker)
        self.assertRaises(sanitize.AssetNotFound, callback)


class TestListNewAddresses(AbsTest, unittest.TestCase):

    def test(self):
        before = self.rw_api.listaddresses("bitcoin")
        newaddress = self.rw_api.newaddress("bitcoin")
        after = self.rw_api.listaddresses("bitcoin")
        self.assertFalse(newaddress in before)
        self.assertTrue(newaddress in after)
        self.assertEquals(len(after), len(before) + 1)


class TestGetAsset(AbsTest, unittest.TestCase):

    def test_uncolored(self):
        moniker = fixtures["getasset"]["uncolored"]["moniker"]
        expected = fixtures["getasset"]["uncolored"]["expected"]
        output = self.ro_api.getasset(moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["getasset"]["epobc"]["moniker"]
        expected = fixtures["getasset"]["epobc"]["expected"]
        output = self.ro_api.getasset(moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["getasset"]["obc"]["moniker"]
        expected = fixtures["getasset"]["obc"]["expected"]
        output = self.ro_api.getasset(moniker)
        self.assertEquals(output, expected)

    def test_undefined(self):
        def callback():
            moniker = fixtures["getasset"]["undefined"]["moniker"]
            self.ro_api.getasset(moniker)
        self.assertRaises(sanitize.AssetNotFound, callback)


class TestBalance(AbsTest, unittest.TestCase):
    # TODO test unconfirmed and available

    def test_uncolored(self):
        moniker = fixtures["getbalance"]["uncolored"]["moniker"]
        expected = fixtures["getbalance"]["uncolored"]["expected"]
        output = self.ro_api.getbalance(moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        moniker = fixtures["getbalance"]["epobc"]["moniker"]
        expected = fixtures["getbalance"]["epobc"]["expected"]
        output = self.ro_api.getbalance(moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        moniker = fixtures["getbalance"]["obc"]["moniker"]
        expected = fixtures["getbalance"]["obc"]["expected"]
        output = self.ro_api.getbalance(moniker)
        self.assertEquals(output, expected)

    def test_undefined(self):
        def callback():
            moniker = fixtures["getbalance"]["undefined"]["moniker"]
            self.ro_api.getbalance(moniker)
        self.assertRaises(sanitize.AssetNotFound, callback)

    def test_all(self):
        expected = fixtures["getbalance"]["all"]["expected"]
        output = self.ro_api.getbalances()
        self.assertEquals(output, expected)


class TestConfig(AbsTest, unittest.TestCase):

    def test_get_set_value(self):
        self.rw_api.setconfigval("testapi", True)
        value = self.rw_api.getconfigval("testapi")
        self.assertEquals(value, True)

        self.rw_api.setconfigval("testapi", False)
        value = self.rw_api.getconfigval("testapi")
        self.assertEquals(value, False)

    def test_dump_import(self):
        config = self.rw_api.dumpconfig()
        config["testapi"] = "testdump"
        path = tempfile.mktemp()
        with open(path, "w") as fobj:
            fobj.write(json.dumps(config))
        self.rw_api.importconfig(path)
        value = self.rw_api.getconfigval("testapi")
        self.assertEquals(value, "testdump")
        os.remove(path)


class TestSignrawtx(AbsTest, unittest.TestCase):

    def test_sign_uncolored(self):
        unsigned = fixtures["signrawtx"]["uncolored"]["unsigned"]
        expected = fixtures["signrawtx"]["uncolored"]["expected"]
        output = self.ro_api.signrawtx(unsigned)
        self.assertEquals(output, expected)

    def test_sign_epobc(self):
        unsigned = fixtures["signrawtx"]["epobc"]["unsigned"]
        expected = fixtures["signrawtx"]["epobc"]["expected"]
        output = self.ro_api.signrawtx(unsigned)
        self.assertEquals(output, expected)

    def test_sign_obc(self):
        unsigned = fixtures["signrawtx"]["obc"]["unsigned"]
        expected = fixtures["signrawtx"]["obc"]["expected"]
        output = self.ro_api.signrawtx(unsigned)
        self.assertEquals(output, expected)


class TestCreatetx(AbsTest, unittest.TestCase):  # TODO test publish

    def test_sign_uncolored(self):
        inputs = fixtures["createtx"]["sign_uncolored"]["inputs"]
        targets = fixtures["createtx"]["sign_uncolored"]["targets"]
        expected = fixtures["createtx"]["sign_uncolored"]["expected"]
        output = self.ro_api.createtx(inputs, targets, sign=True)
        self.assertEquals(output, expected)

    def test_uncolored(self):
        inputs = fixtures["createtx"]["uncolored"]["inputs"]
        targets = fixtures["createtx"]["uncolored"]["targets"]
        expected = fixtures["createtx"]["uncolored"]["expected"]
        output = self.ro_api.createtx(inputs, targets)
        self.assertEquals(output, expected)

    def test_epobc(self):
        inputs = fixtures["createtx"]["epobc"]["inputs"]
        targets = fixtures["createtx"]["epobc"]["targets"]
        expected = fixtures["createtx"]["epobc"]["expected"]
        output = self.ro_api.createtx(inputs, targets)
        self.assertEquals(output, expected)

    def test_sign_epobc(self):
        inputs = fixtures["createtx"]["sign_epobc"]["inputs"]
        targets = fixtures["createtx"]["sign_epobc"]["targets"]
        expected = fixtures["createtx"]["sign_epobc"]["expected"]
        output = self.ro_api.createtx(inputs, targets, sign=True)
        self.assertEquals(output, expected)

    def test_obc(self):
        inputs = fixtures["createtx"]["obc"]["inputs"]
        targets = fixtures["createtx"]["obc"]["targets"]
        expected = fixtures["createtx"]["obc"]["expected"]
        output = self.ro_api.createtx(inputs, targets)
        self.assertEquals(output, expected)

    def test_sign_obc(self):
        inputs = fixtures["createtx"]["sign_obc"]["inputs"]
        targets = fixtures["createtx"]["sign_obc"]["targets"]
        expected = fixtures["createtx"]["sign_obc"]["expected"]
        # FIXME why 2x the same input????!!!
        output = self.ro_api.createtx(inputs, targets, sign=True)
        self.assertEquals(output, expected)


class TestTxoutvalue(AbsTest, unittest.TestCase):

    def test_uncolored(self):
        txid = fixtures["txoutvalue"]["uncolored"]["txid"]
        outindex = fixtures["txoutvalue"]["uncolored"]["outindex"]
        moniker = fixtures["txoutvalue"]["uncolored"]["moniker"]
        expected = fixtures["txoutvalue"]["uncolored"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        txid = fixtures["txoutvalue"]["obc"]["txid"]
        outindex = fixtures["txoutvalue"]["obc"]["outindex"]
        moniker = fixtures["txoutvalue"]["obc"]["moniker"]
        expected = fixtures["txoutvalue"]["obc"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_zero_obc(self):
        txid = fixtures["txoutvalue"]["zero_obc"]["txid"]
        outindex = fixtures["txoutvalue"]["zero_obc"]["outindex"]
        moniker = fixtures["txoutvalue"]["zero_obc"]["moniker"]
        expected = fixtures["txoutvalue"]["zero_obc"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        txid = fixtures["txoutvalue"]["epobc"]["txid"]
        outindex = fixtures["txoutvalue"]["epobc"]["outindex"]
        moniker = fixtures["txoutvalue"]["epobc"]["moniker"]
        expected = fixtures["txoutvalue"]["epobc"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_zero_epobc(self):
        txid = fixtures["txoutvalue"]["zero_epobc"]["txid"]
        outindex = fixtures["txoutvalue"]["zero_epobc"]["outindex"]
        moniker = fixtures["txoutvalue"]["zero_epobc"]["moniker"]
        expected = fixtures["txoutvalue"]["zero_epobc"]["expected"]
        output = self.ro_api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)


if __name__ == '__main__':
    unittest.main()
