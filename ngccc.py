from wallet_controller import WalletController
from pwallet import PersistentWallet
from console_interface import CommandInterpreter

def main():
        import sys
        import getopt
        try:
                opts, args = getopt.getopt(sys.argv[1:], "", [])
        except getopt.GetoptError:
                print "arg error"
                sys.exit(2)
                
        pw = PersistentWallet()
        wallet_model = pw.get_model()
        cominter = CommandInterpreter(wallet_model,
                                      WalletController(wallet_model),
                                      {})
        cominter.run_command(args)

if __name__ == "__main__":
        main()
