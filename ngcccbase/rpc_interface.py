"""
rpc_interface.py

This file connects ngccc-server.py to wallet_controller.py
The main functions that this file has are to take the
JSON-RPC commands from the server and pass them through to
the wallet controller.
Note console_interface.py does a similar thing for ngccc.py
to wallet_controller.py
"""

from wallet_controller import WalletController
from pwallet import PersistentWallet
import pyjsonrpc
import json

# create a global wallet for this use.
wallet = PersistentWallet()
wallet.init_model()
model = wallet.get_model()
controller = WalletController(model)


def get_asset_definition(moniker):
    """Get the asset/color associated with the moniker.
    """
    adm = model.get_asset_definition_manager()
    asset = adm.get_asset_by_moniker(moniker)
    if asset:
        return asset
    else:
        raise Exception("asset %s not found" % moniker)


def balance(moniker):
    """Returns the balance in Satoshi for a particular asset/color.
    "bitcoin" is the generic uncolored coin.
    """
    asset = get_asset_definition(moniker)
    return controller.get_balance(asset)


def addressbalance(moniker):
    """Returns the balance in Satoshi for a particular asset/color.
    "bitcoin" is the generic uncolored coin.
    """
    asset = get_asset_definition(moniker)
    return controller.get_address_balance(asset)


def newaddr(moniker):
    """Creates a new bitcoin address for a given asset/color.
    """
    asset = get_asset_definition(moniker)
    addr = controller.get_new_address(asset)
    return addr.get_address()


def alladdresses(moniker):
    """Lists all addresses for a given asset/color
    """
    asset = get_asset_definition(moniker)
    return [addr.get_address()
            for addr in controller.get_all_addresses(asset)]


def addasset(moniker, color_description):
    """Imports a color definition. This is useful if someone else has
    issued a color and you want to be able to receive it.
    """
    controller.add_asset_definition(
        {"monikers": [moniker],
         "color_set": [color_description]}
        )


def dump_config():
    """Returns a JSON dump of the current configuration
    """
    config = wallet.wallet_config
    dict_config = dict(config.iteritems())
    return json.dumps(dict_config, indent=4)


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


def send(moniker, address, amount):
    """Send some amount of an asset/color to an address
    """
    asset = get_asset_definition(moniker)
    controller.send_coins(address, asset, amount)


def issue(moniker, pck, units, atoms_in_unit):
    """Starts a new color based on <coloring_scheme> with
    a name of <moniker> with <units> per share and <atoms>
    total shares.
    """
    controller.issue_coins(moniker, pck, units, atoms_in_unit)


def scan():
    """Update the database of transactions (amount in each address).
    """
    controller.scan_utxos()


def history(self, **kwargs):
    """print the history of transactions for this color
    """
    asset = self.get_asset_definition(moniker=kwargs['moniker'])
    return self.controller.get_history(asset)


class RPCRequestHandler(pyjsonrpc.HttpRequestHandler):
    """JSON-RPC handler for ngccc's commands.
    The command-set is identical to the console interface.
    """

    methods = {
        "balance": balance,
        "newaddr": newaddr,
        "alladdresses": alladdresses,
        "addasset": addasset,
        "dump_config": dump_config,
        "setval": setval,
        "getval": getval,
        "send": send,
        "issue": issue,
        "scan": scan,
        "history": history,
    }
