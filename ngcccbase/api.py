
import json
import apigen
from time import sleep
from collections import defaultdict
from decimal import Decimal
from ngcccbase.wallet_controller import WalletController
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import HTTPComm
from ngcccbase.p2ptrade.protocol_objects import MyEOffer


class AssetNotFound(Exception):
    def __init__(self, moniker):
        super(AssetNotFound, self).__init__("Asset '%s' not found!" % moniker)


class AddressNotFound(Exception):
    def __init__(self, coloraddress):
        msg = "Address '%s' not found!" % coloraddress
        super(AddressNotFound, self).__init__(msg)


def _print(data):
    print json.dumps(data, indent=2)
    return data


class Ngccc(apigen.Definition):
    """Next-Generation Colored Coin Client interface."""

    def __init__(self, wallet=None, testnet=False):
        if not wallet:
            wallet = "%s.wallet" % ("testnet" if testnet else "mainnet")
        self.wallet = PersistentWallet(wallet, testnet)
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.model)

    def getAssetDefinition(self, moniker):
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if not asset:
          raise AssetNotFound(moniker)
        return asset

    @apigen.command()
    def setconfigval(self, key, value): # FIXME behaviour ok?
        """Sets a value in the configuration.
        Key is expressed as: key.subkey.subsubkey
        """
        kpath = key.split('.')
        value = json.loads(value)
        
        # traverse the path until we get to the value we need to set
        if len(kpath) > 1:
            branch = self.wallet.wallet_config[kpath[0]]
            cdict = branch
            for k in kpath[1:-1]:
                cdict = cdict[k]
            cdict[kpath[-1]] = value
            value = branch
        if kpath[0] in self.wallet.wallet_config:
            self.wallet.wallet_config[kpath[0]] = value
        else:
            # TODO throw error
            pass

    @apigen.command()
    def getconfigval(self, key):
        """Returns the value for a given key in the config.
        Key is expressed as: key.subkey.subsubkey
        """
        if not key:
            print ("getconfigval command expects:  key")
            return
        keys = key.split('.')
        config = self.wallet.wallet_config
        # traverse the path until we get the value
        for key in keys:
            config = config[key]
        return _print(config)

    @apigen.command()
    def dumpconfig(self):
        """Returns a dump of the current configuration."""
        dict_config = dict(self.wallet.wallet_config.iteritems())
        return _print(dict_config)

    @apigen.command()
    def importconfig(self, path): # FIXME what about subkeys and removed keys?
        """Import JSON config."""
        with open(path, 'r') as fp:
            config = json.loads(fp.read())
            wallet_config = self.wallet.wallet_config
            for k in config:
                wallet_config[k] = config[k]

    @apigen.command()
    def issueasset(self, moniker, units, atoms="100000000", scheme="epobc"):
        """ Issue color of name <moniker> with <units> and <atoms> per unit,
        based on <scheme (epobc|obc)>."""
        self.controller.issue_coins(moniker, scheme, int(units), int(atoms))
        # FIXME make quiet, output coming from somewhere
        return self.getasset(moniker)

    @apigen.command()
    def addasset(self, moniker, color_description, unit=100000000):
        """Imports a color/asset definition.
        Enables the use of colors/assets issued by others.
        """
        # TODO test interop with getasset
        self.controller.add_asset_definition({
            "monikers": [moniker],
            "color_set": [color_description],
            "unit" : int(unit)
        })
        return self.getasset(moniker)

    @apigen.command()
    def getasset(self, moniker):
        """Get the asset/color associated with the moniker."""
        # TODO test interop with addasset
        return _print(self.getAssetDefinition(moniker).get_data())

    @apigen.command()
    def listassets(self):
        """Lists all assets/colors registered."""
        assets = self.controller.get_all_assets()
        return _print(map(lambda asset: asset.get_data(), assets))

    def _getbalance(self, asset, unconfirmed, available):
        if unconfirmed:
            balance = self.controller.get_unconfirmed_balance(asset)
        elif available:
            balance = self.controller.get_available_balance(asset)
        else:
            balance = self.controller.get_total_balance(asset)
        return (asset.get_monikers()[0], asset.format_value(balance))

    @apigen.command()
    def getbalance(self, moniker, unconfirmed=False, available=False):
        """Returns the balance for a particular asset/color."""
        asset = self.getAssetDefinition(moniker)
        balance = dict([self._getbalance(asset, unconfirmed, available)])
        return _print(balance)

    @apigen.command()
    def getbalances(self, unconfirmed=False, available=False):
        """Returns the balances for all assets/colors."""
        assets = self.controller.get_all_assets()
        func = lambda asset: self._getbalance(asset, unconfirmed, available)
        balances = dict(map(func, assets))
        return _print(balances)

    @apigen.command()
    def newaddress(self, moniker):
        """Creates a new coloraddress for a given asset/color."""
        asset = self.getAssetDefinition(moniker)
        addressrecord = self.controller.get_new_address(asset)
        coloraddress = addressrecord.get_color_address()
        return _print(coloraddress)

    @apigen.command()
    def listaddresses(self, moniker):
        """Lists all addresses for a given asset/color"""
        asset = self.getAssetDefinition(moniker)
        addressrecords = self.controller.get_all_addresses(asset)
        return _print([ao.get_color_address() for ao in addressrecords])

    @apigen.command()
    def send(self, moniker, coloraddress, amount):
        """Send <coloraddress> given <amount> of an asset/color."""
        asset = self.getAssetDefinition(moniker)
        amount = asset.parse_value(amount)
        self.controller.send_coins(asset, [coloraddress], [int(amount)])
        # TODO print/return txid

    @apigen.command()
    def sendmanycsv(self, path):
        """Send amounts in csv file with format 'moniker,coloraddress,value'."""
        # TODO test if it works correctly
        sendmany_entries = self.controller.parse_sendmany_csv(path)
        self.controller.sendmany_coins(sendmany_entries)
        # TODO print/return txids

    @apigen.command()
    def scan(self):
        """Update the database of transactions."""
        sleep(5)
        self.controller.scan_utxos()

    @apigen.command()
    def fullrescan(self):
        """Rebuild database of wallet transactions."""
        self.controller.full_rescan()

    @apigen.command()
    def history(self, moniker):
        """Show the history of transactions for given asset/color."""
        asset = self.getAssetDefinition(moniker)
        return _print(self.controller.get_history(asset))

    @apigen.command()
    def received(self, moniker):
        """Returns total received amount for each coloraddress
        of a given asset/color.
        """
        asset = self.getAssetDefinition(moniker)
        received = {}
        def reformat(data):
            coloraddress = data['color_address']
            colorvalue = data['value'].get_value()
            return (coloraddress, asset.format_value(colorvalue))
        data = self.controller.get_received_by_address(asset)
        return _print(dict(map(reformat, data)))

    @apigen.command()
    def coinlog(self):
        """Returns the coin transaction log for this wallet."""
        log = defaultdict(list)
        for coin in self.controller.get_coinlog():
            moniker = coin.asset.get_monikers()[0]
            moniker = 'bitcoin' if moniker == '' else moniker
            log[moniker].append({
              'address' : coin.get_address(),
              'txid' : coin.txhash,
              'out' : coin.outindex,
              'colorvalue' : coin.colorvalues[0].get_value(),
              'value' : coin.value,
              'confirmed' : coin.is_confirmed(),
              'spendingtxs' : coin.get_spending_txs(),
            })
        return _print(log)

    @apigen.command()
    def dumpprivkey(self, coloraddress):
        """Private key for a given coloraddress."""
        wam = self.model.get_address_manager()
        for addressrecord in wam.get_all_addresses():
            if coloraddress == addressrecord.get_color_address():
                return _print(addressrecord.get_private_key())
        raise AddressNotFound(coloraddress)

    @apigen.command()
    def dumpprivkeys(self, moniker):
        """Lists all private keys for a given asset/color."""
        asset = self.getAssetDefinition(moniker)
        addressrecords = self.controller.get_all_addresses(asset)
        return _print(map(lambda ar: ar.get_private_key(), addressrecords))

    def init_p2ptrade(self):
        ewctrl = EWalletController(self.model, self.controller)
        config = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        comm = HTTPComm(config, 'http://p2ptrade.btx.udoidio.info/messages')
        return EAgent(ewctrl, config, comm)

    def p2ptrade_make_offer(self, we_sell, moniker, value, price):
        asset = self.getAssetDefinition(moniker)
        value = asset.parse_value(value)
        bitcoin = self.getAssetDefinition('bitcoin')
        price = bitcoin.parse_value(price)
        total = int(Decimal(value)/Decimal(asset.unit)*Decimal(price))
        color_desc = asset.get_color_set().color_desc_list[0]
        sell_side = {"color_spec": color_desc, "value": value}
        buy_side = {"color_spec": "", "value": total}
        if we_sell:
            return MyEOffer(None, sell_side, buy_side)
        else:
            return MyEOffer(None, buy_side, sell_side)

    def p2ptrade_wait(self, agent, wait):
        if wait and wait > 0:
            for _ in xrange(wait):
                agent.update()
                sleep(1)
        else:
            for _ in xrange(4*6):
                agent.update()
                sleep(0.25)

    @apigen.command()
    def p2porders(self): # TODO add asset filter
        """Show peer to peer trade orders"""
        agent = self.init_p2ptrade()
        agent.update()
        offers = []
        for offer in agent.their_offers.values():
            offerdata = offer.get_data()
            offers.append(offerdata)
            print offerdata
        return offers

    @apigen.command()
    def p2psell(self, moniker, amount, price, wait=30):
        """Sell asset/color for bitcoin via peer to peer trade."""
        # FIXME parse_value and make clear what amount and price are
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(True, moniker, amount, price)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent, int(wait))

    @apigen.command()
    def p2pbuy(self, moniker, amount, price, wait=30):
        """Buy asset/color for bitcoin via peer to peer trade."""
        # FIXME parse_value and make clear what amount and price are
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(False, moniker, amount, price)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent, int(wait))


