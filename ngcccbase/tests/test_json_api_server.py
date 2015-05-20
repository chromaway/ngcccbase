#!/usr/bin/env python

import unittest
import subprocess
import pyjsonrpc

class TestJSONAPIServer(unittest.TestCase):

    def setUp(self):
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")

    def test_dumpconfig(self):
        dumped_config = self.client.dumpconfig()
        self.assertTrue(dumped_config.has_key('testnet') )

if __name__ == '__main__':
    unittest.main()

