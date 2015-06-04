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
from ngcccbase import sanitize


class TestJSONAPIServer(unittest.TestCase):   

    def setUp(self):
        self.reset_status()
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    def reset_status(self):
        self.server = None
        self.working_dir = None

    def tearDown(self):
        if self.server:
            os.killpg(os.getpgid(self.server.pid), signal.SIGTERM)
        if self.working_dir:
            shutil.rmtree(self.working_dir)
        self.reset_status()

    def create_server(self, testnet=False):
        self.working_dir = tempfile.mkdtemp()
        config_path = self.working_dir + '/config.json'

        config = {
                "testnet": testnet,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": self.working_dir + "/coloredcoins.wallet"
                  }
        with open(config_path, 'w') as fi:
            json.dump(config, fi)

        self.server = subprocess.Popen('python ngccc-server.py startserver --config_path=%s' % config_path, preexec_fn=os.setsid, shell=True)
        time.sleep(4)        

    def test_default_config(self):
        """See to that server starts and pulls in a config.json file"""
        self.server = subprocess.Popen('python ngccc-server.py startserver', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        self.assertTrue(self.client.dumpconfig().has_key('testnet') )

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
        res = self.client.newaddress('bitcoin')
        self.assertEqual(len(res), 34) # may want a better test, with e.g. python-bitcoinaddress package
        self. assertTrue(sanitize.bitcoin_address(res))

    def test_scan_does_not_throw_exception(self):
        """Make sure that scan and fullrescan return JSON and not 
           something that causes an exception in pyjsonrpc"""
        self.create_server()
        try:
            res = self.client.scan()
        except:
            self.fail('Scan raised an exception\n' + traceback.format_exc())
            pass
        try:
            res = self.client.fullrescan()
        except:
            self.fail('Fullrescan raised an exception\n' + traceback.format_exc())
            pass

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
        private_keys = ['5J7i6VrN6kedk2EfB3eLnJ79bxw5MJyAas8BwKwoziMPyKDrgi4','5KYXdVsaYs7m9oVXmLeRzCPfVTgbYoZEzCW3uQkMBya3vkcaPWT']
        bitcoin_addresses = ['14nsAgexJULTvmsA82455ArmoNRgnxToGj','1PpgeDc29AzZJJ4sr4wn7bHSEeXVJo5B7n']
        self.create_server()
        res = self.client.importprivkeys('bitcoin', wifs = private_keys)
        addresses = self.client.listaddresses('bitcoin')
        for bitcoin_address in bitcoin_addresses:
            self.assertTrue(bitcoin_address in addresses)

if __name__ == '__main__':
    unittest.main()

