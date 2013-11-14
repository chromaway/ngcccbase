"""
console_interface.py

This file connects ngccc.py to wallet_controller.py
The main functions that this file has are to take the command-line
inputs and pass them through to the wallet controller.
Note rpc_interface.py does a similar thing for ngccc-server.py
to wallet_controller.py
"""

import json


class CommandInterpreter(object):
    """Main object for taking commands from ngccc.py and
    passing them through to wallet controller.
    """
    def __init__(self, wallet, controller):
        """Initialize the controller with the objects we need and
        a list of available commands
        """
        self.wallet = wallet
        self.model = wallet.get_model() if wallet else None
        self.controller = controller
        self.command_dict = {
            "balance": self.balance,
            "newaddr": self.newaddr,
            "alladdresses": self.alladdresses,
            "addasset": self.addasset,
            "dump_config": self.dump_config,
            "send": self.send,
            "issue": self.issue,
            "scan": self.scan,
            "setval": self.setval,
            "getval": self.getval,
            "help": self.display_help,
        }

    def run_command(self, command_key, *args):
        """Run a command with a particular key.
        Defaults to "unknown"
        """
        command = self.command_dict.get(command_key, self.unknown)
        command(*args)

    def unknown(self, *args):
        """Let the user know this isn't a real command
        Also, show the usage message.
        """
        print "unknown command"
        self.display_help(*args)

    def get_asset_definition(self, moniker):
        """Helper method for many other commands.
        Returns an AssetDefinition object from wallet_model.py.
        """
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")

    def balance(self, moniker=None):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        if not moniker:
            print "balance command expects:  moniker"
            return
        asset = self.get_asset_definition(moniker)
        print asset.format_value(self.controller.get_balance(asset))

    def newaddr(self, moniker=None):
        """Creates a new bitcoin address for a given asset/color.
        """
        if not moniker:
            print "newaddr command expects:  moniker"
            return
        asset = self.get_asset_definition(moniker)
        addr = self.controller.get_new_address(asset)
        print addr.get_address()

    def alladdresses(self, moniker=None):
        """Lists all addresses for a given asset/color
        """
        if not moniker:
            print "alladdresses command expects:  moniker"
            return
        asset = self.get_asset_definition(moniker)
        print [addr.get_address()
               for addr in self.controller.get_all_addresses(asset)]

    def addasset(self, moniker=None, color_desc=None):
        """Imports a color definition. This is useful if someone else has
        issued a color and you want to be able to receive it.
        """
        if not (moniker and color_desc):
            print "addasset command expects:  moniker color_descriptor"
            return
        self.controller.add_asset_definition(
            {
                "monikers": [moniker],
                "color_set": [color_desc],
            }
        )

    def dump_config(self):
        """Returns a JSON dump of the current configuration
        """
        config = self.wallet.wallet_config
        dict_config = dict(config.iteritems())
        print json.dumps(dict_config, indent=4)

    def setval(self, key=None, value=None):
        """Sets a value in the configuration.
        Key is expressed like so: key.subkey.subsubkey
        """
        if not (key and value):
            print "setval command expects:  key value"
            return
        kpath = key.split('.')
        try:
            value = json.loads(value)
        except ValueError:
            print "didn't understand the value: %s" % value
            return
        try:
            # traverse the path until we get to the value we
            #  need to set
            if len(kpath) > 1:
                branch = self.wallet.wallet_config[kpath[0]]
                cdict = branch
                for k in kpath[1:-1]:
                    cdict = cdict[k]
                cdict[kpath[-1]] = value
                value = branch
            self.wallet.wallet_config[kpath[0]] = value
        except TypeError:
            print "could not set the key: %s" % key

    def getval(self, key=None):
        """Returns the value for a given key in the config.
        Key is expressed like so: key.subkey.subsubkey
        """
        if not key:
            print "getval command expects:  key"
            return
        kpath = key.split('.')
        cv = self.wallet.wallet_config
        try:
            # traverse the path until we get the value
            for k in kpath:
                cv = cv[k]
            print json.dumps(cv)
        except (KeyError, TypeError):
            print "could not find the key: %s" % key

    def send(self, moniker=None, address=None, val=None):
        """Send some amount of an asset/color to an address
        """
        if not (moniker and address and val):
            print "send command expects:  moniker target_address value"
            return
        asset = self.get_asset_definition(moniker)
        value = asset.parse_value(val)
        self.controller.send_coins(address, asset, value)

    def issue(self, moniker=None, coloring_scheme=None,
              units=None, atoms=None):
        """Starts a new color based on <coloring_scheme> with
        a name of <moniker> with <units> per share and <atoms>
        total shares.
        """
        if not (moniker and coloring_scheme and units and atoms):
            print "issue command expects:  moniker pck units atoms_in_unit"
            return
        self.controller.issue_coins(
            moniker, coloring_scheme, int(units), int(atoms))

    def scan(self):
        """Update the database of transactions (amount in each address).
        """
        self.controller.scan_utxos()

    def display_help(self):
        """Display a help message and all available commands
        """
        print 'python ngccc.py command [arguments]'
        print
        print 'available commands:'
        for command in self.command_dict:
            print '\t%s' % command
