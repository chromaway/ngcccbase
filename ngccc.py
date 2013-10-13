from wallet_controller import WalletController
from pwallet import PersistentWallet


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
            assdef = wm.get_asset_definition_manager().get_asset_by_moniker(args[1])
            print ctrl.get_balance(assdef)
        elif command=='newaddr':
            assdef = wm.get_asset_definition_manager().get_asset_by_moniker(args[1])
            addr = ctrl.get_new_address(assdef) 
            print addr.get_address()
        elif command=='alladdresses':
            assdef = wm.get_asset_definition_manager().get_asset_by_moniker(args[1])
            print [addr.get_address() 
                   for addr in ctrl.get_all_addresses(assdef)]                   
        elif command=='addasset':
            moniker = args[1]
            color_desc = args[2]
            ctrl.add_asset_definition({"moniker": moniker,
                                       "color_set": [color_desc]})

if __name__ == "__main__":
        main()
