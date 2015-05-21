#!/usr/bin/env python

import unittest
import os
import signal
import subprocess
import time
import pyjsonrpc

class TestJSONAPIServer(unittest.TestCase):

    def setUp(self):
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")
        self.server = subprocess.Popen('python ngccc-server.py startserver', preexec_fn=os.setsid, shell=True)
        time.sleep(4) # make it settle before calling stuff

    def test_dumpconfig(self):
        dumped_config = self.client.dumpconfig()
        self.assertTrue(dumped_config.has_key('testnet') )

    def tearDown(self):
        os.killpg(os.getpgid(self.server.pid), signal.SIGTERM)

    # def test_load_server_config(self):
#
if __name__ == '__main__':
    unittest.main()

