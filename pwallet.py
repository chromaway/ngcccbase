from wallet_model import WalletModel
from coloredcoinlib import store

class PersistentWallet(object):

    def __init__(self, import_config=None):
        self.store_conn = store.DataStoreConnection("wallet.db")
        self.wallet_config = store.PersistentDictStore(
            self.store_conn.conn, "wallet")
        if import_config:
            self.import_config(import_config)
        self.wallet_model = None

    def init_model(self):
        self.wallet_model = WalletModel(self.wallet_config)

    def import_config(self, config):
        for k in config.iterkeys():
            self.wallet_config[k] = config[k]

    def initialize_new_wallet(self):
        pass

    def get_model(self):
        return self.wallet_model
