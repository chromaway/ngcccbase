from wallet_model import WalletModel
from coloredcoinlib import store
from meat import Address


class PersistentWallet(object):

    def __init__(self, import_config=None):
        self.store_conn = store.DataStoreConnection("wallet.db")
        self.wallet_config = store.PersistentDictStore(
            self.store_conn.conn, "wallet")
        if import_config:
            self.import_config(import_config)
        self.wallet_model = None

    def init_model(self):
        if 'master_key' not in self.wallet_config:
            self.initialize_new_wallet()
        self.wallet_model = WalletModel(self.wallet_config)

    def import_config(self, config):
        for k in config.iterkeys():
            self.wallet_config[k] = config[k]

    def initialize_new_wallet(self):
        master_key = Address.new().privkey
        self.wallet_config['master_key'] = master_key
        self.wallet_config['genesis_color_sets'] = []

    def get_model(self):
        return self.wallet_model
