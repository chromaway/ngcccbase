from pwallet import PersistentWallet
from wallet_controller import WalletController
from wallet_model import AssetDefinition

from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import HTTPExchangeComm
from ngcccbase.p2ptrade.protocol_objects import MyEOffer


class Wallet(object):
    def __init__(self):
        self.wallet = PersistentWallet()
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

    def add_asset(self, params):
        self.controller.add_asset_definition({
            "monikers": [params['moniker']],
            "color_set": [params['color_desc']],
            "unit": params['unit']
        })

    def get_all_asset(self):
        return self.wallet.wallet_config['asset_definitions']

    def issue(self, params):
        self.controller.issue_coins(
            params['moniker'], params['coloring_scheme'],
            params['units'], params['amount'])

    def get_all_monikers(self):
        monikers = [asset.get_monikers()[0] for asset in
            self.model.get_asset_definition_manager().get_all_assets()]
        monikers.remove('bitcoin')
        monikers = ['bitcoin'] + monikers
        return monikers

    def get_balance(self, color):
        return self.controller.get_balance(self.get_asset_definition(color))

    def get_all_addresses(self, color):
        return [addr.get_address() for addr in
            self.controller.get_all_addresses(self.get_asset_definition(color))]

    def get_new_address(self, color):
        return self.controller. \
            get_new_address(self.get_asset_definition(color)).get_address()

    def scan(self):
        self.controller.scan_utxos()

    def send_coins(self, items):
        if isinstance(items, dict):
            items = [items]
        for item in items:
            self.controller.send_coins(
                item['address'],
                item['asset'] if 'asset' in item
                    else self.get_asset_definition(item['moniker']),
                item['value'])

    def p2ptrade_init(self):
        ewctrl = EWalletController(self.model)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = HTTPExchangeComm(
            config, 'http://p2ptrade.btx.udoidio.info/messages')
        self.p2p_agent = EAgent(ewctrl, config, comm)

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

wallet = Wallet()
