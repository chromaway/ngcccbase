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

    def create_livenet_server(self):
        """Start server with custom config on realnet"""
        self.working_dir = tempfile.mkdtemp()
        config_path = self.working_dir + '/config.json'

        config = {
                "testnet": False,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": self.working_dir + "/realnet.wallet"
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
        self.create_livenet_server()
        self.assertFalse(self.client.dumpconfig()['testnet'])

    def test_load_config_testnet(self):
        """Start server with custom config on testnet"""
        config = {
                "testnet": True,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": "/tmp/testnet.wallet"
                  }
        with open('/tmp/config.json', 'w') as fi:
            json.dump(config, fi)

        self.server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        self.assertTrue(self.client.dumpconfig()['testnet'])

    def test_get_new_bitcoin_address(self):
        """Start server with custom config on realnet"""
        self.create_livenet_server()
        res = self.client.newaddress('bitcoin')
        self.assertEqual(len(res), 34) # may want a better test, with e.g. python-bitcoinaddress package
        self. assertTrue(sanitize.bitcoin_address(res))

    def test_scan_does_not_throw_exception(self):
        """Start server with custom config on realnet"""
        self.create_livenet_server()
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
        """Start server with custom config on realnet"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        bitcoin_address = '1Jtkin4FsUcPW3VwcpNsYLmP82wC1ybv1Z'
        self.create_livenet_server()
        res = self.client.importprivkey('bitcoin', private_key)
        addresses = self.client.listaddresses('bitcoin')
        self.assertTrue(bitcoin_address in addresses)

if __name__ == '__main__':
    unittest.main()

