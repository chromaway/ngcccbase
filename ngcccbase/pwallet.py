"""
pwallet.py

A colored-coin wallet implementation that uses a persistent
data-store. The actual storage is in sqlite3 db's via coloredcoinlib
"""

from wallet_model import WalletModel
from coloredcoinlib import store
import sqlite3
import os
import json


class ConfigKeyNotFound(Exception):
    def __init__(self, key):
        super(ConfigKeyNotFound, self).__init__("Key '%s' not found!" % key)



class PersistentWallet(object):
    """Represents a wallet object that stays persistent.
    That is, it doesn't go away every time you run the program.
    """

    def __init__(self, wallet_path, testnet):
        """Create a persistent wallet. If a configuration is passed
        in, put that configuration into the db by overwriting
        the relevant data, never deleting. Otherwise, load with
        the configuration from the persistent data-store.
        """
        if wallet_path is None:
            if testnet:
                wallet_path = "testnet.wallet"
            else:
                wallet_path = "mainnet.wallet"
        new_wallet = not os.path.exists(wallet_path)
        self.store_conn = store.DataStoreConnection(wallet_path, True)
        self.store_conn.conn.row_factory = sqlite3.Row
        self.wallet_config = store.PersistentDictStore(
            self.store_conn.conn, "wallet")
        if new_wallet:
            self.initialize_new_wallet(testnet)
        if testnet and not self.wallet_config['testnet']:
            raise Exception("Not a testnet wallet!")
        self.wallet_model = None

    def getconfig(self):
        return self.wallet_config

    def init_model(self):
        """Associate the wallet model based on the persistent
        configuration.
        """
        self.wallet_model = WalletModel(self.wallet_config, self.store_conn)

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

    def setconfigval(self, key, value): # FIXME behaviour ok?
        kpath = key.split('.')
        value = json.loads(value)

        # traverse the path until we get to the value we need to set
        if len(kpath) > 1:
            branch = self.wallet_config[kpath[0]]
            cdict = branch
            for k in kpath[1:-1]:
                cdict = cdict[k]
            cdict[kpath[-1]] = value
            value = branch
        if kpath[0] in self.wallet_config:
            self.wallet_config[kpath[0]] = value
        else:
            raise ConfigKeyNotFound(key)

    def getconfigval(self, key):
        if not key:
            raise ConfigKeyNotFound(key)
        keys = key.split('.')
        config = self.wallet_config
        # traverse the path until we get the value
        for key in keys:
            config = config[key]
        return config


    def dumpconfig(self):
        return dict(self.wallet_config.iteritems())

    def importconfig(self, path):
        # FIXME what about subkeys and removed keys?
        with open(path, 'r') as fp:
            config = json.loads(fp.read())
            wallet_config = self.wallet_config
            for k in config:
                wallet_config[k] = config[k]

