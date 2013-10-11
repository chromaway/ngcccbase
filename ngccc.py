from wallet_controller import WalletController

def create_wallet_model():
    from wallet_model import WalletModel
    import json

    with open("wallet-config.json", "r") as fp:
        config = json.load(fp)
    return WalletModel(config)

def main():
        import sys
        import getopt
        try:
                opts, args = getopt.getopt(sys.argv[1:], "", [])
        except getopt.GetoptError:
                print "arg error"
                sys.exit(2)
                
        command = args[0]

        wm = create_wallet_model()
        ctrl = WalletController(wm)
        if command=='balance':
            assdef = wm.get_asset_definition_manager().get_asset_by_moniker("bitcoin")
            print ctrl.get_balance(assdef)

if __name__ == "__main__":
        main()
