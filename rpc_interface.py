from wallet_controller import WalletController
from pwallet import PersistentWallet
import pyjsonrpc
import json

wallet = PersistentWallet()
model = wallet.get_model()
controller = WalletController(model)

def get_asset_definition(moniker):
    adm = model.get_asset_definition_manager()
    asset = adm.get_asset_by_moniker(moniker)
    if asset:
        return asset
    else:
        raise Exception("asset not found")

def balance(moniker):
    asset = get_asset_definition(moniker)
    return controller.get_balance(asset)

def newaddr(moniker):
    asset = get_asset_definition(moniker)
    addr = controller.get_new_address(asset)
    return addr.get_address()

def alladdresses(moniker):
    asset = get_asset_definition(moniker)
    return [addr.get_address()
            for addr in controller.get_all_addresses(asset)]

def addasset(moniker, color_description):
    controller.add_asset_definition(
        {"monikers": [moniker],
         "color_set": [color_description]}
        )

def dump_config():
    config = wallet.wallet_config
    dict_config = dict(config.iteritems())
    return json.dumps(dict_config, indent=4)

def send(moniker, address, amount):
    asset = get_asset_definition(moniker)
    controller.send_coins(address, asset, amount)

def issue(moniker, pck, units, atoms_in_unit):
    controller.issue_coins(moniker, pck, units, atoms_in_unit)

def scan():
    controller.scan_utxos()

class RPCRequestHandler(pyjsonrpc.HttpRequestHandler):

    methods = {
        "balance": balance,
        "newaddr": newaddr,
        "alladdresses": alladdresses,
        "addasset": addasset,
        "dump_config": dump_config,
        "send": send,
        "issue": issue,
        "scan": scan,
    }

