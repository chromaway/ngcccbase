

import json
import apigen
from time import sleep
from ngcccbase import sanitize
from collections import defaultdict
from ngcccbase.wallet_controller import WalletController
from ngcccbase.pwallet import PersistentWallet


class AddressNotFound(Exception):
    def __init__(self, coloraddress):
        msg = "Address '%s' not found!" % coloraddress
        super(AddressNotFound, self).__init__(msg)


def _print(data): # TODO move this to apigen
    print json.dumps(data, indent=2)
    return data


class Ngccc(apigen.Definition):
    """Next-Generation Colored Coin Client interface."""

    def __init__(self, wallet=None, testnet=False):

        # sanitize inputs
        testnet = sanitize.flag(testnet)

        if not wallet:
            wallet = "%s.wallet" % ("testnet" if testnet else "mainnet")

        self.wallet = PersistentWallet(wallet, testnet)
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.model)

    @apigen.command()
    def setconfigval(self, key, value):
        """Sets a value in the configuration.
        Key is expressed as: key.subkey.subsubkey
        """

        # sanitize inputs
        key = sanitize.cfgkey(key)
        value = sanitize.cfgvalue(value)

        self.wallet.setconfigval(key, value)


    @apigen.command()
    def getconfigval(self, key):
        """Returns the value for a given key in the config.
        Key is expressed as: key.subkey.subsubkey
        """

        # sanitize inputs
        key = sanitize.cfgkey(key)

        return _print(self.wallet.getconfigval(key))

    @apigen.command()
    def dumpconfig(self):
        """Returns a dump of the current configuration."""
        return _print(self.wallet.dumpconfig())

    @apigen.command()
    def importconfig(self, path):
        """Import JSON config."""
        self.wallet.importconfig(path)

    @apigen.command()
    def issueasset(self, moniker, quantity, unit="100000000", scheme="epobc"):
        """ Issue <quantity> of asset with name <moniker> and <unit> atoms,
        based on <scheme (epobc|obc)>."""

        # sanitize inputs
        moniker = sanitize.moniker(moniker)
        quantity = sanitize.quantity(quantity)
        unit = sanitize.unit(unit)
        scheme = sanitize.scheme(scheme)

        self.controller.issue_coins(moniker, scheme, quantity, unit)
        return self.getasset(moniker)

    @apigen.command()
    def addassetjson(self, data):
        """Add a json asset definition.
        Enables the use of colors/assets issued by others.
        """

        # sanitize inputs
        data = sanitize.jsonasset(data)

        self.controller.add_asset_definition(data)
        return self.getasset(data['monikers'][0])

    @apigen.command()
    def addasset(self, moniker, color_description, unit=100000000):
        """Add a asset definition.
        Enables the use of colors/assets issued by others.
        """

        # sanitize inputs
        moniker = sanitize.moniker(moniker)
        color_description = sanitize.colordesc(color_description)
        unit = sanitize.unit(unit)

        self.controller.add_asset_definition({
            "monikers": [moniker],
            "color_set": [color_description],
            "unit" : unit
        })
        return self.getasset(moniker)

    @apigen.command()
    def getasset(self, moniker):
        """Get the asset associated with the moniker."""
        return _print(sanitize.asset(self.model, moniker).get_data())

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
        """Returns the balance for a particular asset."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)
        unconfirmed = sanitize.flag(unconfirmed)
        available = sanitize.flag(available)

        balance = dict([self._getbalance(asset, unconfirmed, available)])
        return _print(balance)

    @apigen.command()
    def getbalances(self, unconfirmed=False, available=False):
        """Returns the balances for all assets/colors."""

        # sanitize inputs
        unconfirmed = sanitize.flag(unconfirmed)
        available = sanitize.flag(available)

        assets = self.controller.get_all_assets()
        func = lambda asset: self._getbalance(asset, unconfirmed, available)
        balances = dict(map(func, assets))
        return _print(balances)

    @apigen.command()
    def newaddress(self, moniker):
        """Creates a new coloraddress for a given asset."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)

        addressrecord = self.controller.get_new_address(asset)
        coloraddress = addressrecord.get_color_address()
        return _print(coloraddress)

    @apigen.command()
    def listaddresses(self, moniker):
        """Lists all addresses for a given asset"""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)

        addressrecords = self.controller.get_all_addresses(asset)
        return _print([ao.get_color_address() for ao in addressrecords])

    @apigen.command()
    def send(self, moniker, coloraddress, amount):
        """Send <coloraddress> given <amount> of an asset."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)
        coloraddress = sanitize.coloraddress(self.model, asset, coloraddress)
        amount = sanitize.assetamount(asset, amount)

        txid = self.controller.send_coins(asset, [coloraddress], [amount])
        return _print(txid)

    @apigen.command()
    def sendmanyjson(self, data):
        """Send amounts given in json fromatted data.
        Format [{'moniker':"val",'amount':"val",'coloraddress':"val"}]
        All entries must use the same color scheme.
        """

        # sanitize inputs
        sendmany_entries = sanitize.sendmanyjson(self.model, data)

        return _print(self.controller.sendmany_coins(sendmany_entries))

    @apigen.command()
    def sendmanycsv(self, path):
        """Send amounts in csv file with format 'moniker,coloraddress,amount'.
        All entries must use the same color scheme.
        """

        # sanitize inputs
        sendmany_entries = sanitize.sendmanycsv(self.model, path)

        return _print(self.controller.sendmany_coins(sendmany_entries))

    @apigen.command()
    def scan(self):
        """Update the database of transactions."""
        sleep(5) # TODO why sleep?
        self.controller.scan_utxos()

    @apigen.command()
    def fullrescan(self):
        """Rebuild database of wallet transactions."""
        self.controller.full_rescan()

    @apigen.command()
    def history(self, moniker):
        """Show the history of transactions for given asset."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)

        return _print(self.controller.get_history(asset))

    @apigen.command()
    def received(self, moniker):
        """Returns total received amount for each coloraddress
        of a given asset.
        """

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)

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
    def dumpprivkey(self, moniker, coloraddress):
        """Private key for a given coloraddress."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)
        coloraddress = sanitize.coloraddress(self.model, asset, coloraddress)

        wam = self.model.get_address_manager()
        for addressrecord in wam.get_all_addresses():
            if coloraddress == addressrecord.get_color_address():
                return _print(addressrecord.get_private_key())
        raise AddressNotFound(coloraddress)

    @apigen.command()
    def dumpprivkeys(self, moniker):
        """Lists all private keys for a given asset."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)

        addressrecords = self.controller.get_all_addresses(asset)
        return _print(map(lambda ar: ar.get_private_key(), addressrecords))

    @apigen.command()
    def p2porders(self, moniker="", sellonly=False, buyonly=False):
        """Show peer to peer trade orders"""

        # sanitize inputs
        sellonly = sanitize.flag(sellonly)
        buyonly = sanitize.flag(buyonly)
        asset = None
        if moniker and moniker != 'bitcoin':
            asset = sanitize.asset(self.model, moniker)

        return _print(self.controller.p2porders(asset, sellonly, buyonly))

    @apigen.command()
    def p2psell(self, moniker, assetamount, btcprice, wait=30):
        """Sell <assetamount> for <btcprice> via peer to peer trade."""
        self._p2ptrade_make_offer(True, moniker, assetamount, btcprice, wait)

    @apigen.command()
    def p2pbuy(self, moniker, assetamount, btcprice, wait=30):
        """Buy <assetamount> for <btcprice> via peer to peer trade."""
        self._p2ptrade_make_offer(False, moniker, assetamount, btcprice, wait)

    def _p2ptrade_make_offer(self, we_sell, moniker, value, price, wait):

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)
        bitcoin = sanitize.asset(self.model, 'bitcoin')
        value = sanitize.assetamount(asset, value)
        price = sanitize.assetamount(bitcoin, price)
        wait = sanitize.integer(wait)

        self.controller.p2ptrade_make_offer(we_sell, asset, value, price, wait)

    def _get_txout_values(self, txid, outindex, asset):
        def reformat(assetvalue):
            asset, value = assetvalue
            amount = asset.format_value(value)
            moniker = asset.get_monikers()[0]
            return moniker, amount
        result = self.controller.get_txout_assetvalues(txid, outindex, asset)
        return _print(dict(map(reformat, result)))

    @apigen.command()
    def txoutvalue(self, txid, outindex, moniker):
        """Get the transaction output color value for <moniker>."""

        # sanitize inputs
        txid = sanitize.txid(txid)
        outindex = sanitize.positiveinteger(outindex)
        asset = sanitize.asset(self.model, moniker)

        return self._get_txout_values(txid, outindex, asset)

    @apigen.command()
    def txoutvalues(self, txid, outindex):
        """Get the transaction output color values for known assets."""

        # sanitize inputs
        txid = sanitize.txid(txid)
        outindex = sanitize.positiveinteger(outindex)

        return self._get_txout_values(txid, outindex, None)

    @apigen.command()
    def getutxos(self, moniker, amount):
        """ Get unspent transaction outputs for given asset amount."""

        # sanitize inputs
        asset = sanitize.asset(self.model, moniker)
        amount = sanitize.assetamount(asset, amount)

        def reformat(utxo):
            return { 'txid' : utxo.txhash, 'outindex' : utxo.outindex }
        utxos, total = self.controller.get_utxos(asset, amount)
        return _print({ 
          'utxos' : map(reformat, utxos), 
          'total' : asset.format_value(total)
        })

    @apigen.command()
    def createtx(self, inputs, targets, sign=False, publish=False):
        """ Construct an unsigned transaction
        with the given utxo inputs and targets.
        """
        # TODO add flag to disable adding change address
        # TODO add flag to allow partial siging

        # sanitize inputs
        utxos = sanitize.utxos(inputs)
        targets = sanitize.targets(self.model, targets)
        sign = sanitize.flag(sign)
        publish = sanitize.flag(publish)

        return _print(self.controller.createtx(utxos, targets, sign, publish))

    @apigen.command()
    def signrawtx(self, rawtx): # TODO test it
        """ Sign raw transaction. """

        # sanitize inputs
        rawtx = sanitize.rawtx(rawtx)

        return _print(self.controller.sign_rawtx(rawtx))

    @apigen.command()
    def sendrawtx(self, rawtx): # TODO test it
        """ Publish raw transaction to bitcoin network. """

        # sanitize inputs
        rawtx = sanitize.rawtx(rawtx)

        return _print(self.controller.publish_rawtx(rawtx))

