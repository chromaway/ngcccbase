"""
pwallet.py

A colored-coin wallet implementation that uses a persistent
data-store. The actual storage is in sqlite3 db's via coloredcoinlib
"""

from wallet_model import WalletModel
from coloredcoinlib import store


class PersistentWallet(object):
    """Represents a wallet object that stays persistent.
    That is, it doesn't go away every time you run the program.
    """

    def __init__(self, wallet_path=None, import_config=None):
        """Create a persistent wallet. If a configuration is passed
        in, put that configuration into the db by overwriting
        the relevant data, never deleting. Otherwise, load with
        the configuration from the persistent data-store.
        """
        if wallet_path is None:
            wallet_path = "wallet.db"
        self.store_conn = store.DataStoreConnection(wallet_path)
        self.wallet_config = store.PersistentDictStore(
            self.store_conn.conn, "wallet")
        if import_config:
            self.import_config(import_config)
        self.wallet_model = None

    def init_model(self):
        """Associate the wallet model based on the persistent
        configuration.
        """
        self.wallet_model = WalletModel(self.wallet_config)

    def import_config(self, config):
        """Import JSON configuration <config> into the
        persistent data-store.
        """
        for k in config.iterkeys():
            self.wallet_config[k] = config[k]

    def initialize_new_wallet(self):
        """Currently nothing happens here.
        """
        pass

    def get_model(self):
        """Pass back the model associated with the persistent
        wallet.
        """
        return self.wallet_model
