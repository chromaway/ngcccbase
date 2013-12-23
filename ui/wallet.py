from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController
from ngcccbase.asset import AssetDefinition

from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import HTTPComm, ThreadedComm
from ngcccbase.p2ptrade.protocol_objects import MyEOffer

import argparse


class Wallet(object):
    thread_comm = None

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--wallet", dest="wallet_path")
        parsed_args = vars(parser.parse_args())

        self.wallet = PersistentWallet(parsed_args.get('wallet_path'))
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.wallet.get_model())

    def get_asset_definition(self, moniker):
        if isinstance(moniker, AssetDefinition):
            return moniker
        adm = self.wallet.get_model().get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("asset not found")

    def get_asset_definition_by_color_set(self, color_set):
        adm = self.wallet.get_model().get_asset_definition_manager()
        for asset in adm.get_all_assets():
            if color_set in asset.get_color_set().get_data():
                return asset
        raise Exception("asset not found")

    def add_asset(self, params):
        self.controller.add_asset_definition({
            "monikers": [params['moniker']],
            "color_set": [params['color_desc']],
            "unit": params['unit']
        })
        if len(self.get_all_addresses(params['moniker'])) == 0:
            self.get_new_address(params['moniker'])

    def get_all_asset(self):
        return self.wallet.wallet_config['asset_definitions']

    def issue(self, params):
        self.controller.issue_coins(
            params['moniker'], params['coloring_scheme'],
            params['units'], params['atoms'])
        if len(self.get_all_addresses(params['moniker'])) == 0:
            self.get_new_address(params['moniker'])

    def get_all_monikers(self):
        monikers = [asset.get_monikers()[0] for asset in
            self.model.get_asset_definition_manager().get_all_assets()]
        monikers.remove('bitcoin')
        monikers = ['bitcoin'] + monikers
        return monikers

    def get_balance(self, color):
        return self.controller.get_balance(self.get_asset_definition(color))

    def get_all_addresses(self, color):
        return [addr.get_color_address() for addr in
            self.controller.get_all_addresses(self.get_asset_definition(color))]

    def get_address_balance(self, color):
        asset = self.get_asset_definition(color)
        return self.controller.get_address_balance(asset)

    def get_some_address(self, color):
        wam = self.model.get_address_manager()
        cs = self.get_asset_definition(color).get_color_set()
        ar = wam.get_some_address(cs)
        return ar.get_color_address()

    def get_new_address(self, color):
        return self.controller. \
            get_new_address(self.get_asset_definition(color)).get_color_address()

    def scan(self):
        self.controller.scan_utxos()

    def send_coins(self, items):
        if isinstance(items, dict):
            items = [items]
        for item in items:
            self.controller.send_coins(
                item['asset'] if 'asset' in item \
                    else self.get_asset_definition(item['moniker']),
                [item['address']],
                [item['value']])

    def p2ptrade_init(self):
        ewctrl = EWalletController(self.model, self.controller)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = HTTPComm(
            config, 'http://p2ptrade.btx.udoidio.info/messages')
        self.thread_comm = ThreadedComm(comm)
        self.p2p_agent = EAgent(ewctrl, config, self.thread_comm)
        self.thread_comm.start()

    def p2ptrade_stop(self):
        if self.thread_comm is not None:
            self.thread_comm.stop()

    def p2ptrade_make_offer(self, we_sell, params):
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

    def p2ptrade_make_mirror_offer(self, offer):
        data = offer.get_data()
        return MyEOffer(None, data['B'], data['A'], False)

wallet = Wallet()
