"""
pwallet.py

A colored-coin wallet implementation that uses a persistent
data-store. The actual storage is in sqlite3 db's via coloredcoinlib
"""

from wallet_model import WalletModel
from coloredcoinlib import store
import sqlite3
import os


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
            raise Exception("not a testnet wallet")
        self.wallet_model = None

    def init_model(self):
        """Associate the wallet model based on the persistent
        configuration.
        """
        self.wallet_model = WalletModel(
            self.wallet_config, self.store_conn)

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
