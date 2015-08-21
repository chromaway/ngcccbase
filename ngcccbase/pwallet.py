"""
pwallet.py

A colored-coin wallet implementation that uses a persistent
data-store. The actual storage is in sqlite3 db's via coloredcoinlib
"""

import bitcoin
from wallet_model import WalletModel
from coloredcoinlib import store
import sqlite3
import os
import json
from ngcccbase import logger
logger.setup_logging()

class ConfigKeyNotFound(Exception):

    def __init__(self, key):
        super(ConfigKeyNotFound, self).__init__("Key '%s' not found!" % key)


class ConfigPathInUse(Exception):

    def __init__(self, key):
        msg = "Key '%s' intersects value!" % key
        super(ConfigPathInUse, self).__init__(msg)


class PersistentWallet(object):

    """Represents a wallet object that stays persistent.
    That is, it doesn't go away every time you run the program.
    """

    def __init__(self, wallet_path, testnet,
                 use_naivetxdb=False, dryrun=False):
        """Create a persistent wallet. If a configuration is passed
        in, put that configuration into the db by overwriting
        the relevant data, never deleting. Otherwise, load with
        the configuration from the persistent data-store.
        """
        self.dryrun = dryrun
        # FIXME make wallet read only for dryrun
        if wallet_path is None:
            if testnet:
                wallet_path = "testnet.wallet"
            else:
                wallet_path = "mainnet.wallet"
        new_wallet = not os.path.exists(wallet_path)
        self.store_conn = store.DataStoreConnection(wallet_path, True)
        self.store_conn.conn.row_factory = sqlite3.Row

        if not self.dryrun:
            conn = self.store_conn.conn
            self.wallet_config = store.PersistentDictStore(conn, "wallet")
        else:
            self.wallet_config = {}

        if new_wallet:
            self.initialize_new_wallet(testnet)
        if testnet and not self.wallet_config['testnet']:
            raise Exception("Not a testnet wallet!")
        self.wallet_model = None
        self.use_naivetxdb = use_naivetxdb

        if testnet:
            bitcoin.SelectParams('testnet')
        else:
            bitcoin.SelectParams('mainnet')

    def getconfig(self):
        return self.wallet_config

    def init_model(self):
        """Associate the wallet model based on the persistent
        configuration.
        """
        self.wallet_model = WalletModel(self.wallet_config, self.store_conn,
                                        use_naivetxdb=self.use_naivetxdb)

    def disconnect(self):
        if self.wallet_model:
            self.wallet_model.disconnect()
            self.wallet_model = None

    def initialize_new_wallet(self, testnet):
        """New wallets are born in testnet mode until we have a version
        which is safe to be used on mainnet.
        """
        self.wallet_config['testnet'] = testnet

    def get_model(self):
        """Pass back the model associated with the persistent
        wallet.
        """
        return self.wallet_model

    def setconfigval(self, keypath, value):
        keys = keypath.split('.')
        config = dict(self.wallet_config)

        # set in config copy
        branch = config
        while len(keys) > 1:
            if keys[0] not in branch:
                branch[keys[0]] = {}
            branch = branch[keys[0]]
            keys = keys[1:]
            if not isinstance(branch, dict):
                raise ConfigPathInUse(keypath)
        branch[keys[0]] = value

        # set wallet_config from copy
        root_key = keypath.split('.')[0]
        self.wallet_config[root_key] = config[root_key]

    def getconfigval(self, keypath):
        if not keypath:
            raise ConfigKeyNotFound(keypath)
        keys = keypath.split('.')
        branch = self.wallet_config
        for key in keys:
            branch = branch[key]
        return branch

    def importprivkey(self, wif, asset):
        wam = self.wallet_model.get_address_manager()

        # chack if pk already in wallet
        address = wam.find_address_by_wif(wif)
        if address:
            return address

        addr_params = {
            'address_data': wif,
            'color_set': asset.get_color_set().get_data(),
        }

        # add to config
        if not self.wallet_config.get("addresses"):
            self.wallet_config["addresses"] = []
        self.wallet_config["addresses"] += [addr_params]

        # add to address manager
        return wam.add_loose_address(addr_params)

    def dumpconfig(self):
        return dict(self.wallet_config.iteritems())

    def importconfig(self, path):

        # remove previous entries
        for key in self.wallet_config:
            del self.wallet_config[key]

        # add new entries
        with open(path, 'r') as fp:
            config = json.loads(fp.read())
            wallet_config = self.wallet_config
            for key in config:
                wallet_config[key] = config[key]
