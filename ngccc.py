#!/usr/bin/env python
#
# ngccc.py
#
# command-line interface to the Next-Generation Colored Coin Client
# You can manage your colored coins using this command.

from wallet_controller import WalletController
from pwallet import PersistentWallet
from console_interface import CommandInterpreter
import json
import sys
import getopt

# parse the arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "", [])
except getopt.GetoptError:
    print "arg error"
    sys.exit(2)

# use help by default
if len(args) == 0:
    args = ['help']

# special command for importing a json config
if args[0] == 'import_config':
    with open(args[1], "r") as fp:
        config = json.load(fp)
    pw = PersistentWallet(config)
    sys.exit(0)

# load the wallet
pw = PersistentWallet()
try:
    pw.init_model()
except Exception as e:
    print "failed to initialize wallet model: %s" % e

# create the command interpreter
wallet_model = pw.get_model()
controller = WalletController(wallet_model) \
    if wallet_model else None
interpreter = CommandInterpreter(pw, controller)

# run the command
interpreter.run_command(*args)
