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
from ngcccbase.sanitize import colordesc, InvalidInput

SLEEP_TIME = 10  # Time to sleep after the json-rpc server has started
EXECUTABLE = 'python ngccc-server.py'



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

        self.server = subprocess.Popen('%s --config_path=%s'
                                       % (EXECUTABLE, config_path), preexec_fn=os.setsid, shell=True)
        time.sleep(SLEEP_TIME)

    def test_default_config(self):
        """See to that server starts and pulls in a config.json file"""
        self.server = subprocess.Popen('python ngccc-server.py',
                                       preexec_fn=os.setsid, shell=True)
        time.sleep(SLEEP_TIME)
        self.assertTrue(self.client.dumpconfig().has_key('testnet'))

    # def test_load_config_realnet(self):
    #     """Start server with custom config on realnet"""
    #     self.create_server()
    #     self.assertFalse(self.client.dumpconfig()['testnet'])

    def test_load_config_testnet(self):
        """Start server with custom config on testnet"""
        self.create_server(testnet=True)
        self.assertTrue(self.client.dumpconfig()['testnet'])

    def test_get_new_bitcoin_address(self):
        """Generate a new bitcoin address"""
        self.create_server()
        address = self.client.newaddress('bitcoin')
        netcodes = ['BTC','XTN']
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
        self.assertEqual(res['available'], '0.00060519')

    def test_no_dup_importprivkey(self):
        """Test that duplicate imports don't change balance or address count"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        self.create_server()
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        balances = self.client.getbalance('bitcoin')
        self.assertEqual(balances['available'], '0.00060519')
        res = self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        self.assertEqual(len(self.client.listaddresses('bitcoin')), 1)
        self.assertEqual(balances['available'], '0.00060519')

    def test_issue_asset_not_throw_exception(self):
        """Needs funds on mainnet, and they should stay stable at the amount that is tested for."""
        private_key = "5KAtWUcg45VDNB3QftP4V5cwcavBhLj9UWpJCtxsZBBqevGjhZN"
        address = "12WarJccsEjzzf3Aoukh8YJXwxK58qpj8W"  # listed for convenience
        self.create_server()
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan()
        res = self.client.getbalance('bitcoin')
        self.assertTrue(Decimal(res['available']) > Decimal('0.00006'))
        try:
            res = self.client.issueasset('foo_inc', 1000)
        except:
            self.fail('Issueasset raised exception\n' + traceback.format_exc())

    def test_addassetjson(self):
        self.create_server()

        json_data = '''{
                        "assetid": "Bf1aXLmTv41pc2",
                        "color_set": [
                            "epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077"
                        ],
                        "monikers": [
                            "foo_inc"
                        ],
                        "unit": 1
                        }'''
        res = self.client.addassetjson(json.loads(json_data))
        color_set = self.client.getasset('foo_inc')['color_set']
        self.assertEqual(color_set[0], u'epobc:27da3337fb4a5bb8e2e5a537448e5ec9cfaa3c15628c3c333025d547bbcf9d71:0:361077')
        new_address = self.client.newaddress('foo_inc')
        self.assertEqual(new_address, self.client.listaddresses('foo_inc')[0])
        color_part, bitcoin_part = new_address.split('@')
        self.assertTrue(is_address_valid(bitcoin_part, allowable_netcodes=['BTC', 'XTN']))


if __name__ == '__main__':
    # EXECUTABLE = './cw'
    unittest.main()
