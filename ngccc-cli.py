
#!/usr/bin/env python
"""
ngccc-cli.py

command-line interface to the Next-Generation Colored Coin Client
You can manage your colored coins using this command.
"""

import argparse
import os
import json

from ngcccbase.wallet_controller import WalletController
from ngcccbase.pwallet import PersistentWallet


class _ApplicationHelpFormatter(argparse.HelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        argparse.HelpFormatter.add_usage(self, usage, None, groups, prefix)

    def add_argument(self, action):
        if isinstance(action, argparse._SubParsersAction):
            self._add_item(self._format_subparsers, [action])
        else:
            argparse.HelpFormatter.add_argument(self, action)

    def _format_subparsers(self, action):
        max_action_width = max(
            [len(x) for x in action._name_parser_map.keys()])

        parts = []
        for name, subaction in action._name_parser_map.items():
            parts.append("  {name: <{max_action_width}}  {desc}".format(
                name=name,
                desc=subaction.description,
                max_action_width=max_action_width))

        return '\n'.join(parts)


class Application(object):
    def __init__(self):
        self.args = None
        self.parser = argparse.ArgumentParser(
            description="Next-Generation Colored Coin Client "
            "Command-line interface",
            formatter_class=_ApplicationHelpFormatter)

        self.parser.add_argument("--wallet", dest="wallet_path")

        subparsers = self.parser.add_subparsers(
            title='subcommands', dest='command')

        parser = subparsers.add_parser(
            'import_config', description="Import json config.")
        parser.add_argument('path', type=self.validate_import_config_path)

        parser = subparsers.add_parser(
            'setval', description="Sets a value in the configuration.")
        parser.add_argument('key')
        parser.add_argument('value', type=self.validate_JSON_decode)

        parser = subparsers.add_parser(
            'getval', description=
            "Returns the value for a given key in the config.")
        parser.add_argument('key')

        parser = subparsers.add_parser(
            'dump_config', description=
            "Returns a JSON dump of the current configuration.")

        parser = subparsers.add_parser(
            'addasset', description="Imports a color definition.")
        parser.add_argument('moniker')
        parser.add_argument('color_desc')
        parser.add_argument('unit', type=int)

        parser = subparsers.add_parser(
            'issue', description="Starts a new color.")
        parser.add_argument('moniker')
        parser.add_argument('coloring_scheme')
        parser.add_argument('units', type=int)
        parser.add_argument('atoms', type=int)

        parser = subparsers.add_parser(
            'newaddr', description=
            "Creates a new bitcoin address for a given asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'alladdresses', description=
            "Lists all addresses for a given asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'allassets', description="Lists all assets registered.")

        parser = subparsers.add_parser(
            'balance', description=
            "Returns the balance in Satoshi for a particular asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'addressbalance', description=
            "Returns the balance in Satoshi for each address "
            "of a particular asset/color.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'send', description=
            "Send some amount of an asset/color to an address.")
        parser.add_argument('moniker')
        parser.add_argument('address')
        parser.add_argument('value')

        parser = subparsers.add_parser(
            'scan', description=
            "Update the database of transactions (amount in each address).")

        parser = subparsers.add_parser(
            'history', description="Shows the history of transactions "
            "for a particular asset/color in your wallet.")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'p2p_show_orders', description="Show p2ptrade orders")
        parser.add_argument('moniker')

        parser = subparsers.add_parser(
            'p2p_sell', description="sell via p2ptrade")
        parser.add_argument('moniker')
        parser.add_argument('value')
        parser.add_argument('price')

        parser = subparsers.add_parser(
            'p2p_buy', description="buy via p2ptrade")
        parser.add_argument('moniker')
        parser.add_argument('value')
        parser.add_argument('price')

    def __getattribute__(self, name):
        if name in ['controller', 'model', 'wallet']:
            try:
                data = self.data
            except AttributeError:
                self.data = data = {}

                pw = PersistentWallet(self.args.get('wallet_path'))
                pw.init_model()

                wallet_model = pw.get_model()

                data.update({
                    'controller': WalletController(wallet_model)
                    if wallet_model else None,
                    'wallet': pw,
                    'model': wallet_model if pw else None,
                    })
            return data[name]
        return object.__getattribute__(self, name)

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

    def validate_import_config_path(self, path):
        return self.validate_JSON_decode(self.validate_file_read(path))

    def validate_file_read(self, path):
        try:
            with open(path, 'r') as fp:
                return fp.read()
        except IOError:
            msg = "Can't read file: %s." % path
            raise argparse.ArgumentTypeError(msg)

    def validate_JSON_decode(self, s):
        try:
            return json.loads(s)
        except ValueError:
            msg = "No JSON object could be decoded: %s." % s
            raise argparse.ArgumentTypeError(msg)

    def validate_config_key(self, key):
        wc = self.wallet.wallet_config
        try:
            for name in key.split('.'):
                wc = wc[name]
        except KeyError:
            msg = "Can't find the key: %s." % key
            raise argparse.ArgumentTypeError(msg)
        return key

    def start(self):
        args = vars(self.parser.parse_args())
        self.args = args
        if 'command' in args:
            getattr(self, "command_{command}".format(**args))(**args)

    def command_import_config(self, **kwargs):
        """Special command for importing a JSON config.
        """
        pw = PersistentWallet(kwargs.get('wallet_path'), kwargs['path'])

    def command_setval(self, **kwargs):
        """Sets a value in the configuration.
        Key is expressed like so: key.subkey.subsubkey
        """
        keys = kwargs['key'].split('.')
        value = kwargs['value']
        wc = self.wallet.wallet_config
        if len(keys) > 1:
            branch = wc[keys[0]]
            cdict = branch
            for key in keys[1:-1]:
                cdict = cdict[key]
            cdict[keys[-1]] = value
            value = branch
        wc[keys[0]] = value

    def command_getval(self, **kwargs):
        """Returns the value for a given key in the config.
        Key is expressed like so: key.subkey.subsubkey
        """
        wc = self.wallet.wallet_config
        for name in kwargs['key'].split('.'):
            wc = wc[name]
        print (json.dumps(wc, indent=4))

    def command_dump_config(self, **kwargs):
        """Returns a JSON dump of the current configuration.
        """
        config = self.wallet.wallet_config
        dict_config = dict(config.iteritems())
        print (json.dumps(dict_config, indent=4))

    def command_addasset(self, **kwargs):
        """Imports a color definition. This is useful if someone else has
        issued a color and you want to be able to receive it.
        """
        self.controller.add_asset_definition({
            "monikers": [kwargs['moniker']],
            "color_set": [kwargs['color_desc']],
            "unit": kwargs['unit']
        })

    def command_issue(self, **kwargs):
        """Starts a new color based on <coloring_scheme> with
        a name of <moniker> with <units> per share and <atoms>
        total shares.
        """
        self.controller.issue_coins(
            kwargs['moniker'], kwargs['coloring_scheme'],
            kwargs['units'], kwargs['atoms'])

    def command_newaddr(self, **kwargs):
        """Creates a new bitcoin address for a given asset/color.
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        addr = self.controller.get_new_address(asset)
        print (addr.get_color_address())

    def command_alladdresses(self, **kwargs):
        """Lists all addresses for a given asset/color
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        for addr in self.controller.get_all_addresses(asset):
            print (addr.get_color_address())

    def command_allassets(self, **kwargs):
        """Lists all assets (moniker/color_hash) registered
        """
        for asset in self.controller.get_all_assets():
            print ("%s: %s" % (', '.join(asset.monikers),
                              asset.get_color_set().get_color_hash()))

    def command_addressbalance(self, **kwargs):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        for row in self.controller.get_address_balance(asset):
            print ("%s: %s" % (row['color_address'],
                              asset.format_value(row['value'])))

    def command_balance(self, **kwargs):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        print (asset.format_value(self.controller.get_balance(asset)))

    def command_send(self, **kwargs):
        """Send some amount of an asset/color to an address
        """
        asset = self.get_asset_definition(kwargs['moniker'])
        value = asset.parse_value(kwargs['value'])
        self.controller.send_coins(asset, [kwargs['address']], [value])

    def command_scan(self, **kwargs):
        """Update the database of transactions (amount in each address).
        """
        self.controller.scan_utxos()

    def command_history(self, **kwargs):
        """print the history of transactions for this color
        """
        asset = self.get_asset_definition(moniker=kwargs['moniker'])
        history = self.controller.get_history(asset)
        for item in history:
            mempool = "(mempool)" if item['mempool'] else ""
            print ("%s %s %s %s" % (
                item['action'], item['value'], item['address'], mempool))

    def init_p2ptrade(self):
        from ngcccbase.p2ptrade.ewctrl import EWalletController
        from ngcccbase.p2ptrade.agent import EAgent
        from ngcccbase.p2ptrade.comm import HTTPComm

        ewctrl = EWalletController(self.model, self.controller)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = HTTPComm(
            config, 'http://p2ptrade.btx.udoidio.info/messages')
        agent = EAgent(ewctrl, config, comm)
        return agent

    def p2ptrade_make_offer(self, we_sell, params):
        from ngcccbase.p2ptrade.protocol_objects import MyEOffer
        asset = self.get_asset_definition(params['moniker'])
        value = asset.parse_value(params['value'])
        bitcoin = self.get_asset_definition('bitcoin')
        price = bitcoin.parse_value(params['price'])
        total = int(float(value)/float(asset.unit)*float(price))
        color_desc = asset.get_color_set().color_desc_list[0]
        sell_side = {"color_spec": color_desc, "value": value}
        buy_side = {"color_spec": "", "value": total}
        if we_sell:
            return MyEOffer(None, sell_side, buy_side)
        else:
            return MyEOffer(None, buy_side, sell_side)

    def p2ptrade_wait(self, agent):
        #  TODO: use config/parameters
        for _ in xrange(30):
            agent.update()

    def command_p2p_show_orders(self, **kwargs):
        agent = self.init_p2ptrade()
        agent.update()
        for offer in agent.their_offers.values():
            print (offer.get_data())

    def command_p2p_sell(self, **kwargs):
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(True, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent)

    def command_p2p_buy(self, **kwargs):
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(False, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent)


if __name__ == "__main__":
    Application().start()
