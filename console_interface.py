import json

class CommandInterpreter(object):
    def __init__(self, wallet, controller, params):
        self.wallet = wallet
        self.model = wallet.get_model()
        self.controller = controller
        self.command_dict = {
                "balance": self.balance,
                "newaddr": self.newaddr,
                "alladdresses": self.alladdresses,
                "addasset": self.addasset,
                "dump_config": self.dump_config
        }

    def run_command(self, args):
        command = self.command_dict.get(args[0], self.unknown)
        command(args)

    def unknown(self, args):
        print "unknown command"

    def get_asset_definition(self, moniker):
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")

    def balance(self, args):
        asset = self.get_asset_definition(args[1])
        print self.controller.get_balance(asset)

    def newaddr(self, args):
        asset = self.get_asset_definition(args[1])
        addr = self.controller.get_new_address(asset)
        print addr.get_address()

    def alladdresses(self, args):
        asset = self.get_asset_definition(args[1])
        print [addr.get_address()
                   for addr in self.controller.get_all_addresses(asset)]

    def addasset(self, args):
        moniker = args[1]
        color_desc = args[2]
        self.controller.add_asset_definition(
                {"monikers": [moniker],
                 "color_set": [color_desc]}
        )

    def dump_config(self, args):
        config = self.wallet.wallet_config
        dict_config = dict(config.iteritems())
        print json.dumps(dict_config, indent=4)
