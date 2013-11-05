import json

class CommandInterpreter(object):
    def __init__(self, wallet, controller, params):
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
                "getval": self.getval
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
        print asset.format_value(self.controller.get_balance(asset))

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

    def setval(self, args):
        kpath = args[1].split('.')
        value = json.loads(args[2])
        if len(kpath) > 1:
            branch = self.wallet.wallet_config[kpath[0]]
            cdict = branch
            for k in kpath[1:-1]:
                cdict = cdict[k]
            cdict[kpath[-1]] = value
            value = branch
        self.wallet.wallet_config[kpath[0]] = value

    def getval(self, args):
        kpath = args[1].split('.')
        cv = self.wallet.wallet_config
        for k in kpath:
            cv = cv[k]
        print json.dumps(cv)

    def send(self, args):
        asset = self.get_asset_definition(args[1])
        value = asset.parse_value(args[3])
        self.controller.send_coins(args[2], asset, value)

    def issue(self, args):
        self.controller.issue_coins(args[1], args[2], int(args[3]), int(args[4]))

    def scan(self, args):
        self.controller.scan_utxos()
