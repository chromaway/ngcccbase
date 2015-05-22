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

    def test_load_config_realnet(self):
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
        dumped_config = self.client.dumpconfig()
        self.assertTrue(dumped_config.has_key('testnet') )
        self.assertFalse(dumped_config['testnet'])
        # killing server, and its child process (that would be HTTPServer)
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)

    def test_load_config_testnet(self):
        config = {
                "testnet": True,
                "port": 8080,
                "hostname": "localhost",
                "wallet_path": "/tmp/testnet.wallet"
                  }

        server = subprocess.Popen('python ngccc-server.py startserver --config_path=/tmp/config.json', preexec_fn=os.setsid, shell=True)
        time.sleep(4)
        with open('/tmp/config.json', 'w') as fi:
            json.dump(config, fi)
        dumped_config = self.client.dumpconfig()
        self.assertTrue(dumped_config.has_key('testnet') )
        self.assertFalse(dumped_config['testnet'])

        # killing server, and its child process (that would be HTTPServer)
        os.killpg(os.getpgid(server.pid), signal.SIGTERM)
#
if __name__ == '__main__':
    unittest.main()

