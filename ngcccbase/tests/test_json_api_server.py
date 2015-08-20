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
import inspect
import logging
import time
import urllib2
from decimal import Decimal
from pycoin.key.validate import is_address_valid
from ngcccbase.sanitize import colordesc, InvalidInput
from ngcccbase import logger

logger.setup_logging()
logger = logging.getLogger('ngcccbase')
logger.info(__file__ + ' loaded\n****************************************************')


SLEEP_TIME = 5  # Time to sleep after the json-rpc server starts
START_DIR = os.getcwd()
EXECUTABLE = 'python %s/ngccc-server.py' % START_DIR
BLOCKCHAIN_HEADERS_CACHE = os.path.dirname(os.path.realpath(__file__))
cache_initialized = False

class RegtestControl():

    def __init__(self, url):
        self.control = pyjsonrpc.HttpClient(url=url)

    def wait_for_new_block_height(self, old_height):
        while True:
            current_height = self.control.getblockcount()
            if current_height > old_height:
                return current_height
            time.sleep(5)

    def add_confirmations(self, confirmations):
        current_height = self.control.getblockcount()
        try:
            result = self.control.add_confirmations(confirmations)
        except urllib2.HTTPError:
            new_height = self.wait_for_new_block_height(current_height)
            return {'result':new_height}
        return result


class TestJSONAPIServer(unittest.TestCase):

    def setUp(self):
        self.reset_status()
        self.client = pyjsonrpc.HttpClient(url="http://localhost:8080")
        self.secondary_client = pyjsonrpc.HttpClient(url="http://localhost:8081")

    def tearDown(self):
        if self.server:
            os.killpg(os.getpgid(self.server.pid), signal.SIGTERM)
        if self.secondary_server:
            os.killpg(os.getpgid(self.secondary_server.pid), signal.SIGTERM)
        if self.working_dir:
            shutil.rmtree(self.working_dir)
        if self.secondary_working_dir:
            shutil.rmtree(self.secondary_working_dir)
        self.reset_status()

    def reset_status(self):
        self.server = None
        self.working_dir = None
        self.secondary_server = None
        self.secondary_working_dir = None

    def _initialize_blockchain_headers_cache(self):
        """Produces/updates the cached blockchain headers files for mainnet and testnet"""
        global cache_initialized
        # import pdb;pdb.set_trace()

        if not cache_initialized:
            self.setUp()
            working_dir = tempfile.mkdtemp()
            secondary_working_dir = tempfile.mkdtemp()

            mainnet_cache = "%s/mainnet.blockchain_headers" % BLOCKCHAIN_HEADERS_CACHE
            testnet_cache = "%s/testnet.blockchain_headers" % BLOCKCHAIN_HEADERS_CACHE

            mainnet_updated = "%s/mainnet.blockchain_headers" % working_dir
            testnet_updated = "%s/testnet.blockchain_headers" % secondary_working_dir

            if os.path.exists(mainnet_cache):
                shutil.copy(mainnet_cache, mainnet_updated)

            if os.path.exists(testnet_cache):
                shutil.copy(testnet_cache, testnet_updated)

            self.create_server(use_cached_blockchain=False, working_dir=working_dir)
            self.client.scan(force_synced_headers=True)

            self.create_server(testnet=True, secondary=True, port=8081, use_cached_blockchain=False, working_dir=secondary_working_dir)
            self.secondary_client.scan(force_synced_headers=True)

            shutil.copy(mainnet_updated, mainnet_cache)
            shutil.copy(testnet_updated, testnet_cache)

            self.tearDown()
            cache_initialized = True

    def copy_in_blockchain_file(self, target_dir, testnet=False):
        '''Supplies a ready made blockchain file'''
        prefix = 'testnet' if testnet else 'mainnet'
        source = "%s/%s.blockchain_headers" % (BLOCKCHAIN_HEADERS_CACHE, prefix)
        destination = "%s/%s.blockchain_headers" % (target_dir, prefix)
        shutil.copy(source, destination)

    def create_server(self, testnet=False, wallet_path=None, port=8080, regtest_server=None, secondary=False, use_cached_blockchain=True, working_dir=None):
        '''Flexible server creator, used by the tests'''
        if use_cached_blockchain:
            self._initialize_blockchain_headers_cache()
        logger.info( "Create server called from %s" % inspect.stack()[1][3])
        working_dir = working_dir if working_dir else tempfile.mkdtemp()
        config_path = working_dir + '/config.json'
        if wallet_path is None:
            wallet_path = working_dir + "/coloredcoins.wallet"
        config = {
            "testnet": testnet,
            "port": port,
            "hostname": "localhost",
            "wallet_path": wallet_path,
            "regtest_server": regtest_server
        }
        with open(config_path, 'w') as fi:
            json.dump(config, fi)
        os.chdir(working_dir)
        if use_cached_blockchain:
            self.copy_in_blockchain_file(target_dir=working_dir, testnet=testnet)
        server = subprocess.Popen('%s --config_path=%s'
                                  % (EXECUTABLE, config_path), preexec_fn=os.setsid, shell=True)
        os.chdir(START_DIR)
        if secondary:
            self.secondary_server = server
            self.secondary_working_dir = working_dir
        else:
            self.server = server
            self.working_dir = working_dir
        time.sleep(SLEEP_TIME)


    # def test_default_config(self):
    #     """See to that server starts and pulls in a config.json file"""
    #     self.server = subprocess.Popen('python ngccc-server.py',
    #                                    preexec_fn=os.setsid, shell=True)
    #     time.sleep(SLEEP_TIME)
    #     self.assertTrue(self.client.dumpconfig().has_key('testnet'))

    def test_load_config_realnet(self):
        """Starts server with custom config on mainnet"""
        self.create_server()
        self.assertFalse(self.client.dumpconfig()['testnet'])

    def test_load_config_testnet(self):
        """Starts server with a custom config on testnet"""
        self.create_server(testnet=True)
        self.assertTrue(self.client.dumpconfig()['testnet'])

    def test_get_new_bitcoin_address(self):
        """Generates a new bitcoin address"""
        self.create_server()
        address = self.client.newaddress('bitcoin')
        netcodes = ['BTC', ]
        self.assertTrue(bool(is_address_valid(address, allowable_netcodes=netcodes)))

    def test_scan_does_not_throw_exception(self):
        """Makes sure that scan and fullrescan return JSON and not
           something that causes an exception in pyjsonrpc server-side"""
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
        """Tests importing a private key"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        bitcoin_address = '1Jtkin4FsUcPW3VwcpNsYLmP82wC1ybv1Z'
        self.create_server()
        res = self.client.importprivkey('bitcoin', private_key)
        addresses = self.client.listaddresses('bitcoin')
        self.assertTrue(bitcoin_address in addresses)

    def test_get_balance(self):
        """ Tests to see if a non zero balance can be retrieved from mainnet"""
        self.create_server()
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan(force_synced_headers=True)
        self.client.scan()  # FIXME waiting for bug to be resolved, should then be deleted
        res = self.client.getbalance('bitcoin')
        self.assertEqual(res['available'], '0.00060519')

    def test_no_dup_importprivkey(self):
        """Tests that duplicate imports don't change balance or address count"""
        private_key = '5JTuHqTdknhZSnk5pBZaqWDaSuhz6xmJEc9fH9UXgvpZbdRNsLq'
        self.create_server()
        self.client.importprivkey('bitcoin', private_key)
        self.client.scan(force_synced_headers=True)
        self.client.scan()  # FIXME waiting for bug to be resolved, should then be deleted

        balances = self.client.getbalance('bitcoin')
# 0.00060519
        self.assertEqual(balances['available'], '0.00060519')
        res = self.client.importprivkey('bitcoin', private_key)
        self.client.scan(force_synced_headers=True)
        self.client.scan()  # FIXME waiting for bug to be resolved, should then be deleted

        self.assertEqual(len(self.client.listaddresses('bitcoin')), 1)
        self.assertEqual(balances['available'], '0.00060519')

    # def test_issue_asset_not_throw_exception(self):
    #     """Needs funds on mainnet, and they should stay stable at the amount that is tested for."""
    #     private_key = "5KAtWUcg45VDNB3QftP4V5cwcavBhLj9UWpJCtxsZBBqevGjhZN"
    # address = "12WarJccsEjzzf3Aoukh8YJXwxK58qpj8W"  # listed for convenience
    #     self.create_server()
    #     self.client.importprivkey('bitcoin', private_key)
    #     self.client.scan(force_synced_headers=True)
    # self.client.scan() # FIXME waiting for bug to be resolved, should then be deleted

    #     res = self.client.getbalance('bitcoin')
    #     self.assertTrue(Decimal(res['available']) > Decimal('0.0002'))
    #     try:
    #         res = self.client.issueasset('foo_inc', 1000)
    #     except:
    #         self.fail('Issueasset raised exception\n' + traceback.format_exc())

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

    def test_send(self):
        '''Tests that an asset can be issued and parts of it transferred to
           another party'''
        regtest_server = 'http://chromanode-regtest.webworks.se'
        private_key = '92tYMSp7wkq1UjGDQothg8dh6Mu2cQB87aBG3NXzL44qAyqSEBU'
        regtest_control = RegtestControl(regtest_server + '/regtest/')
        # import pdb;pdb.set_trace()
        result = regtest_control.add_confirmations(1)
        logger.info('Result from adding one block: %s' % result)

        # Server that will issue the asset:
        self.create_server(testnet=True, regtest_server=regtest_server,use_cached_blockchain=False)

        logger.debug('Working dir is %s' % self.working_dir)

        self.client.importprivkey('bitcoin', private_key)
        # import pdb;pdb.set_trace()
        # time.sleep(20) # wait for asyncutxo fetcher
        self.client.fullrescan(force_synced_headers=True)

        self.client.issueasset('foo_inc', 1000)
        exported_asset_json = json.dumps(self.client.getasset('foo_inc'))

        # Server that will import the asset definition
        # and receive the asset transfer
        self.create_server(secondary=True, port=8081, testnet=True, regtest_server=regtest_server, use_cached_blockchain=False)
        self.secondary_client.addassetjson(json.loads(exported_asset_json))
        color_address = self.secondary_client.newaddress('foo_inc')

        # Send the asset over
        result = regtest_control.add_confirmations(1)
        self.client.send('foo_inc', color_address, 10)
        result = regtest_control.add_confirmations(1)
        logger.info('Result from adding one block: %s' % result)
        self.client.fullrescan(force_synced_headers=True)


        # Check that is has arrived
        self.secondary_client.fullrescan(force_synced_headers=True)
        balance = self.secondary_client.getbalance('foo_inc')
        logger.info( balance)


if __name__ == '__main__':
    # EXECUTABLE = './cw'
    unittest.main()
