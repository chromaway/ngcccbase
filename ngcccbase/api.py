
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


# COMMAND               ported validation errors testcli testrpc

# setconfigval          yes    no         no     no      no
# getconfigval          yes    no         no     no      no
# dumpconfig            yes    no         no     no      no
# importconfig          yes    no         no     no      no

# issueasset            yes    no         no     no      no
# getasset              yes    no         no     no      no
# addasset              yes    no         no     no      no
# listassets            yes    no         no     no      no
# balance               yes    no         no     no      no

# newaddress            yes    no         no     no      no
# listaddresses         yes    no         no     no      no
# send                  yes    no         no     no      no
# scan                  yes?   no         no     no      no
# history               yes?   no         no     no      no
# received              yes    no         no     no      no
# privatekeys           yes    no         no     no      no
# coinlog               yes    no         no     no      no
# sendmanycsv           yes?   no         no     no      no
# fullrescan            yes?   no         no     no      no

# p2porders             no     no         no     no      no
# p2psell               no     no         no     no      no
# p2pbuy                no     no         no     no      no


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
        return adm.get_asset_by_moniker(moniker)

    @apigen.command()
    def getasset(self, moniker):
        """Get the asset/color associated with the moniker."""
        asset = self.getAssetDefinition(moniker)
        if not asset:
          pass # FIXME handle error
        data = asset.get_data()
        print json.dumps(data, indent=2)
        return data

    @apigen.command()
    def newaddress(self, moniker):
        """Creates a new address for a given asset/color."""
        asset = self.getAssetDefinition(moniker)
        address = self.controller.get_new_address(asset).get_color_address()
        print address
        return address

    @apigen.command()
    def listaddresses(self, moniker):
        """Lists all addresses for a given asset/color"""
        asset = self.getAssetDefinition(moniker)
        addressobjs = self.controller.get_all_addresses(asset)
        addresses = [ao.get_color_address() for ao in addressobjs]
        for address in addresses:
            print address
        return addresses

    @apigen.command()
    def history(self, moniker):
        """Show the history of transactions for given asset/color."""
        asset = self.getAssetDefinition(moniker)
        history = self.controller.get_history(asset)
        for item in history:
            _item = item.copy()
            _item['mempool'] = "(mempool)" if item['mempool'] else ""
            print ("%(action)s %(value)s %(address)s %(mempool)s" % _item)
        return history


    @apigen.command()
    def scan(self):
        """Update the database of transactions."""
        sleep(5)
        self.controller.scan_utxos()

    @apigen.command()
    def issueasset(self, moniker, units, atoms="100000000", scheme="epobc"):
        """ Issue color of name <moniker> with <units> and <atoms> per unit,
        based on <scheme (epobc|obc)>."""
        self.controller.issue_coins(moniker, scheme, int(units), int(atoms))
        # FIXME rest is quiet
        # FIXME print asset
        # FIXME return asset

    @apigen.command()
    def send(self, moniker, address, amount):
        """Send <amount> in satoshis of <moniker> to an <address>."""
        asset = self.getAssetDefinition(moniker)
        self.controller.send_coins(asset, [address], [int(amount)])

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
        print json.dumps(config, indent=2)
        return config

    @apigen.command()
    def dumpconfig(self):
        """Returns a dump of the current configuration."""
        dict_config = dict(self.wallet.wallet_config.iteritems())
        print json.dumps(dict_config, indent=2)
        return dict_config

    @apigen.command()
    def addasset(self, moniker, color_description, unit=100000000):
        """Imports a color definition.
        Enables the use of colors issued by others.
        """
        self.controller.add_asset_definition({
            "monikers": [moniker],
            "color_set": [color_description],
            "unit" : int(unit)
        })

    @apigen.command()
    def balance(self, moniker, unconfirmed=False, available=False):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.getAssetDefinition(moniker)
        if unconfirmed:
            balance = self.controller.get_unconfirmed_balance(asset)
        elif available:
            balance = self.controller.get_available_balance(asset)
        else:
            balance = self.controller.get_total_balance(asset)
        print balance
        return balance

    @apigen.command()
    def listassets(self):
        """Lists all assets registered."""
        assets = []
        for asset in self.controller.get_all_assets():
            assets.append(asset.get_data())
            monikers = ', '.join(asset.monikers)
            color_hash = asset.get_color_set().get_color_hash()
            print "%s: %s" % (monikers, color_hash)
        return assets

    @apigen.command()
    def importconfig(self, path): # FIXME what about subkeys and removed keys?
        """Import JSON config."""
        with open(path, 'r') as fp:
            config = json.loads(fp.read())
            wallet_config = self.wallet.wallet_config
            for k in config:
                wallet_config[k] = config[k]

    @apigen.command()
    def received(self, moniker):
        """Returns total received amount for each address
        of a given asset/color.
        """
        asset = self.getAssetDefinition(moniker)
        received = {}
        for row in self.controller.get_received_by_address(asset):
            address = row['color_address']
            colorvalue = row['value']
            received[address] = colorvalue.get_value()
            print ("%s: %s" % (address, colorvalue.get_value()))
        return received

    @apigen.command()
    def privatekeys(self, moniker):
        """Lists all private keys for a given asset/color."""
        asset = self.getAssetDefinition(moniker)
        pks = []
        for addr in self.controller.get_all_addresses(asset):
            pk = addr.get_private_key()
            pks.append(pk)
            print pk
        return pks

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
        print json.dumps(log, indent=2)
        return log

    @apigen.command()
    def sendmanycsv(self, path):
        """Send amounts in csv file with format 'moniker,address,value'."""
        print "Sending amounts listed in %s." % path
        sendmany_entries = self.controller.parse_sendmany_csv(path)
        self.controller.sendmany_coins(sendmany_entries)

    @apigen.command()
    def fullrescan(self):
        """Rebuild database of wallet transactions."""
        self.controller.full_rescan()

    def init_p2ptrade(self):
        ewctrl = EWalletController(self.model, self.controller)
        config = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        comm = HTTPComm(config, 'http://p2ptrade.btx.udoidio.info/messages')
        agent = EAgent(ewctrl, config, comm)
        return agent

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
    def p2porders(self):
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
    def p2psell(self, moniker, amount, price, wait):
        """Sell asset/color for bitcoin via peer to peer trade."""
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(True, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent, int(wait))

    @apigen.command()
    def p2pbuy(self, moniker, amount, price, wait):
        """Buy asset/color for bitcoin via peer to peer trade."""
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(False, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent, int(wait))


