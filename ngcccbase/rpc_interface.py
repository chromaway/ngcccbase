"""
rpc_interface.py

This file connects ngccc-server.py to wallet_controller.py
The main functions that this file has are to take the
JSON-RPC commands from the server and pass them through to
the wallet controller.
Note console_interface.py does a similar thing for ngccc.py
to wallet_controller.py
"""

import json
import pyjsonrpc
from wallet_controller import WalletController
from pwallet import PersistentWallet

# COMMAND              implemented  tested
# import_config        no           no   
# setval               no           no   
# getval               no           no   
# dump_config          no           no   
# addasset             no           no   
# issue                no           no   
# newaddr              yes          partial
# alladdresses         no           no   
# privatekeys          no           no   
# allassets            no           no   
# balance              no           no   
# received_by_address  no           no   
# coinlog              no           no   
# send                 no           no   
# sendmany_csv         no           no   
# scan                 no           no   
# full_rescan          no           no   
# history              no           no   
# p2p_show_orders      no           no   
# p2p_sell             no           no
# p2p_buy              no           no


class RPCRequestHandler(pyjsonrpc.HttpRequestHandler):
    """JSON-RPC handler for ngccc's commands.
    The command-set is identical to the console interface.
    """

    def __init__(self, *args, **kwargs):
        super(RPCRequestHandler, self).__init__(*args, **kwargs)
        args = self.server.args
        self.wallet = PersistentWallet(args["wallet"], args['testnet'])
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.model)

    @pyjsonrpc.rpcmethod
    def get_asset_definition(self, moniker):
        """Get the asset/color associated with the moniker.
        """
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("Asset '%s' not found!" % moniker)

    @pyjsonrpc.rpcmethod
    def balance(self, moniker):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.get_asset_definition(moniker)
        return self.controller.get_available_balance(asset)

    @pyjsonrpc.rpcmethod
    def addressbalance(self, moniker):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.get_asset_definition(moniker)
        return self.controller.get_address_balance(asset)

    @pyjsonrpc.rpcmethod
    def newaddr(self, moniker):
        """Creates a new bitcoin address for a given asset/color.
        """
        try:
          asset = self.get_asset_definition(moniker)
        except:
          raise pyjsonrpc.JsonRpcError(
            message = u"Asset '%s' not found!" % moniker,
            code = 32602
          )
        addr = self.controller.get_new_address(asset)
        address = addr.get_address()
        return address

    @pyjsonrpc.rpcmethod
    def alladdresses(self, moniker):
        """Lists all addresses for a given asset/color
        """
        asset = self.get_asset_definition(moniker)
        return [addr.get_address()
                for addr in self.controller.get_all_addresses(asset)]

    @pyjsonrpc.rpcmethod
    def addasset(self, moniker, color_description):
        """Imports a color definition. This is useful if someone else has
        issued a color and you want to be able to receive it.
        """
        self.controller.add_asset_definition(
            {"monikers": [moniker],
             "color_set": [color_description]}
            )

    @pyjsonrpc.rpcmethod
    def dump_config(self):
        """Returns a JSON dump of the current configuration
        """
        config = self.wallet.wallet_config
        dict_config = dict(config.iteritems())
        return json.dumps(dict_config, indent=4)

    @pyjsonrpc.rpcmethod
    def setval(self, key, value):
        """Sets a value in the configuration.
        Key is expressed like so: key.subkey.subsubkey
        """
        if not (key and value):
            print ("setval command expects:  key value")
            return
        kpath = key.split('.')
        try:
            value = json.loads(value)
        except ValueError:
            print ("didn't understand the value: %s" % value)
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
            print ("could not set the key: %s" % key)

    @pyjsonrpc.rpcmethod
    def getval(self, key):
        """Returns the value for a given key in the config.
        Key is expressed like so: key.subkey.subsubkey
        """
        if not key:
            print ("getval command expects:  key")
            return
        kpath = key.split('.')
        cv = self.wallet.wallet_config
        try:
            # traverse the path until we get the value
            for k in kpath:
                cv = cv[k]
            print (json.dumps(cv))
        except (KeyError, TypeError):
            print ("could not find the key: %s" % key)

    @pyjsonrpc.rpcmethod
    def send(self, moniker, address, amount):
        """Send some amount of an asset/color to an address
        """
        asset = self.get_asset_definition(moniker)
        self.controller.send_coins(address, asset, amount)

    @pyjsonrpc.rpcmethod
    def issue(self, moniker, pck, units, atoms_in_unit):
        """Starts a new color based on <coloring_scheme> with
        a name of <moniker> with <units> per share and <atoms>
        total shares.
        """
        self.controller.issue_coins(moniker, pck, units, atoms_in_unit)

    @pyjsonrpc.rpcmethod
    def scan(self):
        """Update the database of transactions (amount in each address).
        """
        self.controller.scan_utxos()

    @pyjsonrpc.rpcmethod
    def history(self, **kwargs):
        """print the history of transactions for this color
        """
        asset = self.get_asset_definition(moniker=kwargs['moniker'])
        return self.controller.get_history(asset)


