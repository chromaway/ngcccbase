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
        print "WORKING DIR", self.working_dir
        config_path = self.working_dir + '/config.json'
        if wallet_path is None:
            self.working_dir + "/coloredcoins.wallet"
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
        time.sleep(1)

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
            self.fail('Fullrescan raised an exception\n' + traceback.format_exc())

    def test_importprivkey(self):
        """Test of importing private keys"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        bitcoin_address = '1Jtkin4FsUcPW3VwcpNsYLmP82wC1ybv1Z'
        self.create_server()
        res = self.client.importprivkey('bitcoin', private_key)
        addresses = self.client.listaddresses('bitcoin')
        self.assertTrue(bitcoin_address in addresses)

    def test_importprivkeys(self):
        """Test of importing private keys"""
        private_keys = ['5J7i6VrN6kedk2EfB3eLnJ79bxw5MJyAas8BwKwoziMPyKDrgi4',
                        '5KYXdVsaYs7m9oVXmLeRzCPfVTgbYoZEzCW3uQkMBya3vkcaPWT']
        bitcoin_addresses = ['14nsAgexJULTvmsA82455ArmoNRgnxToGj',
                             '1PpgeDc29AzZJJ4sr4wn7bHSEeXVJo5B7n']
        self.create_server()
        res = self.client.importprivkeys('bitcoin', wifs=private_keys)
        addresses = self.client.listaddresses('bitcoin')
        for bitcoin_address in bitcoin_addresses:
            self.assertTrue(bitcoin_address in addresses)

if __name__ == '__main__':
    unittest.main()
