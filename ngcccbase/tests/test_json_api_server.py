#!/usr/bin/env python
import unittest
import traceback
import os
import signal
import subprocess
import time
import shutil
import tempfile
import json
import pyjsonrpc
from decimal import Decimal
from pycoin.key.validate import is_address_valid


class TestJSONAPIServer(unittest.TestCase):

    def setUp(self):
        self.reset_status()
        self.client = pyjsonrpc.HttpClient(url="http://localhost:8080")

    def reset_status(self):
        self.server = None
        self.working_dir = None

    def tearDown(self):
        if self.server:
            os.killpg(os.getpgid(self.server.pid), signal.SIGTERM)
        if self.working_dir:
            shutil.rmtree(self.working_dir)
        self.reset_status()

    def create_server(self, testnet=False, wallet_path=None, port=8080):
        self.working_dir = tempfile.mkdtemp()
        # print "WORKING DIR", self.working_dir
        config_path = self.working_dir + '/config.json'
        if wallet_path is None:
            wallet_path = self.working_dir + "/coloredcoins.wallet"
        config = {
            "testnet": testnet,
            "port": port,
            "hostname": "localhost",
            "wallet_path": wallet_path
        }
        with open(config_path, 'w') as fi:
            json.dump(config, fi)

        self.server = subprocess.Popen('python ngccc-server.py startserver --config_path=%s'
                                       % config_path, preexec_fn=os.setsid, shell=True)
        time.sleep(4)

    def test_default_config(self):
        """See to that server starts and pulls in a config.json file"""
        self.server = subprocess.Popen('python ngccc-server.py startserver',
                                       preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        self.assertTrue(self.client.dumpconfig().has_key('testnet'))

    def test_load_config_realnet(self):
        """Start server with custom config on realnet"""
        self.create_server()
        self.assertFalse(self.client.dumpconfig()['testnet'])

    def test_load_config_testnet(self):
        """Start server with custom config on testnet"""
        self.create_server(testnet=True)
        self.assertTrue(self.client.dumpconfig()['testnet'])

    def test_get_new_bitcoin_address(self):
        """Generate a new bitcoin address"""
        self.create_server()
        address = self.client.newaddress('bitcoin')
        netcodes = ['BTC']
        self.assertTrue(bool(is_address_valid(address, allowable_netcodes=netcodes)))

    def test_scan_does_not_throw_exception(self):
        """Make sure that scan and fullrescan return JSON and not
           something that causes an exception in pyjsonrpc"""
        self.create_server()
        try:
            res = self.client.scan()
        except:
            self.fail('Scan raised an exception\n' + traceback.format_exc())
        try:
            res = self.client.fullrescan()
        except:
            self.fail('Fullrescan raised exception\n' + traceback.format_exc())

    def test_importprivkey(self):
        """Test of importing private keys"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        bitcoin_address = '1Jtkin4FsUcPW3VwcpNsYLmP82wC1ybv1Z'
        self.create_server()
        res = self.client.importprivkey('bitcoin', private_key)
        addresses = self.client.listaddresses('bitcoin')
        self.assertTrue(bitcoin_address in addresses)

    def test_get_balance(self):
        """ Test to see if a non zero balance cam be retrieved from mainnet"""
        self.create_server()
        # Should be funded with 0.1 mbtc
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        res = self.client.getbalance('bitcoin')
        self.assertEqual(res['bitcoin'], '0.0001')

    def test_no_dup_importprivkey(self):
        """Test that duplicate imports don't change balance or address count"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        self.create_server()
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        balances = self.client.getbalance('bitcoin')
        self.assertEqual(balances['bitcoin'], '0.0001')
        res = self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        self.assertEqual(len(self.client.listaddresses('bitcoin')), 1)
        self.assertEqual(balances['bitcoin'], '0.0001')

    def test_issue_asset_not_throw_exception(self):
        """Needs funds on mainnet."""
        private_key = "5KAtWUcg45VDNB3QftP4V5cwcavBhLj9UWpJCtxsZBBqevGjhZN"
        address = "12WarJccsEjzzf3Aoukh8YJXwxK58qpj8W" # listed for convenience
        self.create_server()
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        res = self.client.getbalance('bitcoin')
        self.assertTrue(Decimal(res['bitcoin']) > Decimal('0.00006'))
        try:
            res = self.client.issueasset('foo_inc', 1000)
        except:
            self.fail('Issueasset raised exception\n' + traceback.format_exc())

if __name__ == '__main__':
    unittest.main()
