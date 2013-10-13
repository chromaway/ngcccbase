from wallet_model import WalletModel
from coloredcoinlib import store

# [verification needed]
class PersistentWallet(object):
    def __init__(self, import_config = None):
        self.store_conn = store.DataStoreConnection("wallet.db")
        self.wallet_config = store.PersistentDictStore(self.store_conn.conn, "wallet")
        if import_config:
            self.import_config(import_config)
        if not ('ccc' in self.wallet_config):
            self.initialize_new_wallet()
        self.wallet_model = WalletModel(self.wallet_config)

    def import_config(self, config):
        for k in config.iterkeys():
            self.wallet_config[k] = config[k]

    def initialize_new_wallet(self):
        self.wallet_config['ccc'] = {"bitcoind_url": "http://bitcoinrpc:8oso9n8E1KnTexnKHn16N3tcsGpfEThksK4ojzrkzn3b@localhost:8332/"}

    def get_model(self):
        return self.wallet_model
