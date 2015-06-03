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


# def create_livenet_server():
#     """Start server with custom config on realnet"""
#     workingdir = tempfile.mkdtemp()

#     config = {
#             "testnet": False,
#             "port": 8080,
#             "hostname": "localhost",
#             "wallet_path": "/tmp/realnet.wallet"
#               }
#     with open(workingdir + '/config.json', 'w') as fi:
#         json.dump(config, fi)

#     server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
#     time.sleep(4)


class TestJSONAPIServer(unittest.TestCase):   

    def setUp(self):
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    def tearDown(self):
        pass

    def test_default_config(self):
        """See to that server starts and pulls in a config.json file"""
        server = subprocess.Popen('python ngccc-server.py startserver', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        self.assertTrue(self.client.dumpconfig().has_key('testnet') )
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)

    def test_load_config_realnet(self):
        """Start server with custom config on realnet"""
        config = {
                "testnet": False,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": "/tmp/realnet.wallet"
                  }
        with open('/tmp/config.json', 'w') as fi:
            json.dump(config, fi)

        server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        self.assertFalse(self.client.dumpconfig()['testnet'])
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)




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

        server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        self.assertTrue(self.client.dumpconfig()['testnet'])
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)

    def test_get_new_bitcoin_address(self):
        """Start server with custom config on realnet"""
        config = {
                "testnet": False,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": "/tmp/realnet.wallet"
                  }
        with open('/tmp/config.json', 'w') as fi:
            json.dump(config, fi)

        server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        res = self.client.newaddress('bitcoin')
        self.assertEqual(len(res), 34) # may want a better test, with e.g. python-bitcoinaddress package
        self. assertTrue(sanitize.bitcoin_address(res))
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)

    def test_scan_does_not_throw_exception(self):
        """Start server with custom config on realnet"""
        config = {
                "testnet": False,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": "/tmp/realnet.wallet"
                  }
        with open('/tmp/config.json', 'w') as fi:
            json.dump(config, fi)

        server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        try:
            res = self.client.scan()
        except:
            self.fail('Scan raised an exception\n' + traceback.format_exc())
        try:
            res = self.client.fullrescan()
        except:
            self.fail('Fullrescan raised an exception\n' + traceback.format_exc())
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)


    def test_importprivkey(self):
        """Start server with custom config on realnet"""
        config = {
                "testnet": False,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": "/tmp/realnet.wallet"
                  }
        with open('/tmp/config.json', 'w') as fi:
            json.dump(config, fi)
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        bitcoin_address = '1Jtkin4FsUcPW3VwcpNsYLmP82wC1ybv1Z'
        server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        res = self.client.importprivkey('bitcoin', private_key)
        self.assertEqual(len(res), 34) # may want a better test, with e.g. python-bitcoinaddress package
        self.assertTrue(sanitize.bitcoin_address(res))
        addresses = self.client.listaddresses('bitcoin')
        self.assertTrue(bitcoin_address in addresses)
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)

if __name__ == '__main__':
    unittest.main()

