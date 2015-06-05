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


def start_server(testnet, working_dir):
    config = {
        "testnet": "--testnet" if testnet else "",
        "port": "8080",
        "hostname": "localhost",
        "wallet": working_dir + "/coloredcoins.wallet"
    }
    cmd = ('python ngccc-cli.py --wallet="%(wallet)s" %(testnet)s startserver'
           ' --hostname="%(hostname)s" --port="%(port)s"') % config
    return subprocess.Popen(cmd, preexec_fn=os.setsid, shell=True)


class TestMainnet(unittest.TestCase):   

    def setUp(self):
        # setup server
        self.working_dir = tempfile.mkdtemp()
        self.server = start_server(False, self.working_dir)
        time.sleep(4)        

        # setup client
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")
    
    def tearDown(self):
        if self.server:
            os.killpg(os.getpgid(self.server.pid), signal.SIGTERM)
        if self.working_dir:
            shutil.rmtree(self.working_dir)

    def test_config_mainnet(self):
        """Start server with custom config on realnet"""
        self.assertFalse(self.client.dumpconfig()['testnet'])

    def test_get_new_bitcoin_address(self):
        """Generate a new bitcoin address"""
        res = self.client.newaddress('bitcoin')
        self.assertEqual(len(res), 34) # may want a better test, with e.g. python-bitcoinaddress package
        self. assertTrue(sanitize.bitcoin_address(res))

    def test_scan_does_not_throw_exception(self):
        """Make sure that scan and fullrescan return JSON and not 
           something that causes an exception in pyjsonrpc"""
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
        res = self.client.importprivkey('bitcoin', private_key)
        addresses = self.client.listaddresses('bitcoin')
        self.assertTrue(bitcoin_address in addresses)

    def test_importprivkeys(self):
        """Test of importing private keys"""
        private_keys = ['5J7i6VrN6kedk2EfB3eLnJ79bxw5MJyAas8BwKwoziMPyKDrgi4','5KYXdVsaYs7m9oVXmLeRzCPfVTgbYoZEzCW3uQkMBya3vkcaPWT']
        bitcoin_addresses = ['14nsAgexJULTvmsA82455ArmoNRgnxToGj','1PpgeDc29AzZJJ4sr4wn7bHSEeXVJo5B7n']
        
        wifs = json.dumps(private_keys)
        res = self.client.importprivkeys('bitcoin', wifs=wifs)
        addresses = self.client.listaddresses('bitcoin')
        for bitcoin_address in bitcoin_addresses:
            self.assertTrue(bitcoin_address in addresses)


class TestTestnet(unittest.TestCase):   

    def setUp(self):
        # setup server
        self.working_dir = tempfile.mkdtemp()
        self.server = start_server(True, self.working_dir)
        time.sleep(4)        

        # setup client
        self.client = pyjsonrpc.HttpClient(url = "http://localhost:8080")
    
    def tearDown(self):
        if self.server:
            os.killpg(os.getpgid(self.server.pid), signal.SIGTERM)
        if self.working_dir:
            shutil.rmtree(self.working_dir)

    def test_config_testnet(self):
        """Start server with custom config on testnet"""
        self.assertTrue(self.client.dumpconfig()['testnet'])


if __name__ == '__main__':
    unittest.main()

