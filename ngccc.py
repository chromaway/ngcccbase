from wallet_controller import WalletController

class PersistentWallet(object):
    def __init__(self):
        from wallet_model import WalletModel
        from coloredcoinlib import store

        self.store_conn = store.DataStoreConnection("wallet.db")
        self.wallet_config = store.PersistentDictStore(self.store_conn.conn, "wallet")
        if not ('ccc' in self.wallet_config):
            self.initialize_new_wallet()
        self.wallet_model = WalletModel(self.wallet_config)
    def initialize_new_wallet(self):
        self.wallet_config['ccc'] = {"bitcoind_url": "http://bitcoinrpc:8oso9n8E1KnTexnKHn16N3tcsGpfEThksK4ojzrkzn3b@localhost:8332/"}
    def get_model(self):
        return self.wallet_model


def main():
        import sys
        import getopt
        try:
                opts, args = getopt.getopt(sys.argv[1:], "", [])
        except getopt.GetoptError:
                print "arg error"
                sys.exit(2)
                
        command = args[0]

        pw = PersistentWallet()
        wm = pw.get_model()
        ctrl = WalletController(wm)
        if command=='balance':
            assdef = wm.get_asset_definition_manager().get_asset_by_moniker("bitcoin")
            print ctrl.get_balance(assdef)
        elif command=='newaddr':
            assdef = wm.get_asset_definition_manager().get_asset_by_moniker("bitcoin")
            addr = ctrl.get_new_address(assdef) 
            print addr.get_address()

if __name__ == "__main__":
        main()
