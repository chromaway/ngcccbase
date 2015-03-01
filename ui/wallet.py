from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController
from ngcccbase.asset import AssetDefinition

from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import HTTPComm, ThreadedComm
from ngcccbase.p2ptrade.protocol_objects import MyEOffer

from ngcccbase.utxo_fetcher import AsyncUTXOFetcher

import time
import argparse
import threading
from decimal import Decimal


class TimedAsyncTask(threading.Thread):
    def __init__(self, task, sleep_time):
        super(TimedAsyncTask, self).__init__()
        self._stop = threading.Event()
        self.sleep_time = sleep_time
        self.task = task

    def run(self):
        while not self._stop.is_set():
            self.task()
            time.sleep(self.sleep_time)

    def stop(self):
      self._stop.set()


class Wallet(object):
    thread_comm = None

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--wallet", dest="wallet_path")
        parser.add_argument("--testnet", action='store_true')
        parsed_args = vars(parser.parse_args())

        self.wallet = PersistentWallet(parsed_args.get('wallet_path'),
                                       parsed_args.get('testnet'))
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.wallet.get_model())
        self.async_utxo_fetcher = AsyncUTXOFetcher(
            self.model, self.wallet.wallet_config.get('utxo_fetcher', {}))

        self.update_connected_thread = TimedAsyncTask(self.update_connected, 2.5)
        self.update_connected_thread.start()
        self.update_connected()

    def connected(self):
        return self.is_connected

    def update_connected(self):
        try:
            for moniker in self.get_all_monikers():
                asset = self.get_asset_definition(moniker)
                address = self.get_some_address(asset)
                total_balance = self.get_total_balance(asset)
            self.is_connected = self.async_utxo_fetcher.interface.connected()
        except:
            raise
            self.is_connected = False

    def get_asset_definition(self, moniker):
        if isinstance(moniker, AssetDefinition):
            return moniker
        adm = self.wallet.get_model().get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("Asset '%s' not found!" % moniker)

    def get_asset_definition_by_color_set(self, color_set):
        adm = self.wallet.get_model().get_asset_definition_manager()
        for asset in adm.get_all_assets():
            if color_set in asset.get_color_set().get_data():
                return asset
        raise Exception("Asset not found!")

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

    def get_available_balance(self, color):
        return self.controller.get_available_balance(
            self.get_asset_definition(color))

    def get_total_balance(self, color):
        return self.controller.get_total_balance(
            self.get_asset_definition(color))

    def get_unconfirmed_balance(self, color):
        return self.controller.get_unconfirmed_balance(
            self.get_asset_definition(color))

    def get_all_addresses(self, color):
        return [addr.get_color_address() for addr in
            self.controller.get_all_addresses(self.get_asset_definition(color))]

    def get_received_by_address(self, color):
        asset = self.get_asset_definition(color)
        return self.controller.get_received_by_address(asset)

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
        config = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        self.thread_comm = ThreadedComm(
            config, 'http://p2ptrade.btx.udoidio.info/messages'
        )
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
        total = int(Decimal(value)/Decimal(asset.unit)*Decimal(price))
        color_desc = asset.get_color_set().color_desc_list[0]
        sell_side = {"color_spec": color_desc, "value": value}
        buy_side = {"color_spec": "", "value": total}
        if we_sell:
            return MyEOffer(None, sell_side, buy_side)
        else:
            return MyEOffer(None, buy_side, sell_side)

    def p2ptrade_make_mirror_offer(self, offer):
        data = offer.get_data()
        return MyEOffer(None, data['B'], data['A'])

    def stop_all(self):
        self.update_connected_thread.stop()
        self.update_connected_thread.join()
        self.async_utxo_fetcher.stop()
        self.p2ptrade_stop()
        if hasattr(self.model.txdb, 'vbs'):
            self.model.txdb.vbs.stop()


wallet = Wallet()
