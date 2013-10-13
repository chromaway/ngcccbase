from wallet_controller import WalletController
from pwallet import PersistentWallet
from console_interface import CommandInterpreter
import json

def main():
        import sys
        import getopt
        try:
                opts, args = getopt.getopt(sys.argv[1:], "", [])
        except getopt.GetoptError:
                print "arg error"
                sys.exit(2)

        # special command
        if args[0] == 'import_config':
            with open(args[1], "r") as fp:
                config = json.load(fp)
            pw = PersistentWallet(config)
            sys.exit(0)
                
        pw = PersistentWallet()
        wallet_model = pw.get_model()
        cominter = CommandInterpreter(pw,
                                      WalletController(wallet_model),
                                      {})
        cominter.run_command(args)

if __name__ == "__main__":
        main()
