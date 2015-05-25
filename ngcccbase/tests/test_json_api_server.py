#!/usr/bin/env python

import unittest
import os
import signal
import subprocess
import time
import json
import pyjsonrpc

class TestJSONAPIServer(unittest.TestCase):        

    def setUp(self):
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    def tearDown(self):
        pass

    def test_default_config(self):
        """See to that server starts and pulls in config.json file"""
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
#
if __name__ == '__main__':
    unittest.main()

