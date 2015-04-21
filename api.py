#!/usr/bin/env python

import json
import apigen
from ngcccbase.wallet_controller import WalletController
from ngcccbase.pwallet import PersistentWallet

# COMMAND               added fixed validation errors testcli testrpc

# setconfigval          yes   yes   no         no     no      no
# getconfigval          yes   yes   no         no     no      no
# dumpconfig            yes   yes   no         no     no      no
# importconfig          yes   yes   no         no     no      no

# issueasset            yes   no    no         no     no      no
# getasset              yes   no    no         no     no      no
# addasset              yes   no    no         no     no      no
# listassets            yes   no    no         no     no      no
# newaddress            yes   no    no         no     no      no
# listaddresses         yes   no    no         no     no      no
# balance               yes   no    no         no     no      no
# send                  yes   no    no         no     no      no
# scan                  yes   no    no         no     no      no
# history               yes   no    no         no     no      no
# received              yes   no    no         no     no      no
# privatekeys           yes   no    no         no     no      no
# coinlog               yes   no    no         no     no      no
# sendmanycsv           yes   no    no         no     no      no
# fullrescan            yes   no    no         no     no      no
# p2porders             yes   no    no         no     no      no
# p2psell               yes   no    no         no     no      no
# p2pbuy                yes   no    no         no     no      no


class Ngccc(apigen.Definition):
    """Next-Generation Colored Coin Client Command-line interface"""

    def __init__(self, wallet=None, testnet=False):
        if not wallet:
          wallet = "%s.wallet" % ("testnet" if testnet else "mainnet")
        self.wallet = PersistentWallet(wallet, testnet)
        self.wallet.init_model()
        self.model = self.wallet.get_model()
        self.controller = WalletController(self.model)

    @apigen.command()
    def getasset(self, moniker):
        """Get the asset/color associated with the moniker."""
        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker(moniker)
        if asset:
            return asset
        else:
            raise Exception("Asset '%s' not found!" % moniker)

    @apigen.command()
    def newaddress(self, moniker):
        """Creates a new address for a given asset/color."""
        asset = self.getasset(moniker)
        return self.controller.get_new_address(asset).get_color_address()

    @apigen.command()
    def listaddresses(self, moniker):
        """Lists all addresses for a given asset/color"""
        asset = self.getasset(moniker)
        addresses = self.controller.get_all_addresses(asset)
        return [addr.get_color_address() for addr in addresses]

    @apigen.command()
    def history(self, moniker):
        """Show the history of transactions for given asset/color."""
        asset = self.getasset(moniker)
        return self.controller.get_history(asset)

    @apigen.command()
    def scan(self):
        """Update the database of transactions."""
        self.controller.scan_utxos()

    @apigen.command()
    def issueasset(self, moniker, units, atoms="100000000", scheme="epobc"):
        """ Issue color of name <moniker> with <units> and <atoms> per unit,
        based on <scheme>."""
        self.controller.issue_coins(moniker, scheme, int(units), int(atoms))

    @apigen.command()
    def send(self, moniker, address, amount):
        """Send some amount of an asset/color to an address."""
        asset = self.getasset(moniker)
        self.controller.send_coins(address, asset, amount)

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
        print json.dumps(config)
        return config

    @apigen.command()
    def dumpconfig(self):
        """Returns a dump of the current configuration."""
        dict_config = dict(self.wallet.wallet_config.iteritems())
        print json.dumps(dict_config, indent=2)
        return dict_config

    @apigen.command()
    def addasset(self, moniker, color_description):
        """Imports a color definition.
        Enables the use of colors issued by others.
        """
        self.controller.add_asset_definition({
            "monikers": [moniker],
            "color_set": [color_description]
        })

    @apigen.command()
    def balance(self, moniker):
        """Returns the balance in Satoshi for a particular asset/color.
        "bitcoin" is the generic uncolored coin.
        """
        asset = self.getasset(moniker)
        return self.controller.get_available_balance(asset)

    @apigen.command()
    def listassets(self):
        """Lists all assets registered."""
        for asset in self.controller.get_all_assets():
            print ("%s: %s" % (', '.join(asset.monikers),
                              asset.get_color_set().get_color_hash()))

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
        asset = self.get_asset_definition(moniker)
        for row in self.controller.get_received_by_address(asset):
            print ("%s: %s" % (row['color_address'],
                              asset.format_value(row['value'])))

    @apigen.command()
    def privatekeys(self, moniker):
        """Lists all private keys for a given asset/color."""
        asset = self.get_asset_definition(moniker)
        for addr in self.controller.get_all_addresses(asset):
            print (addr.get_private_key())

    @apigen.command()
    def coinlog(self):
        """Returns the coin transaction log for this wallet."""
        moniker = ''
        for coin in self.controller.get_coinlog():
            if coin.asset.get_monikers()[0] != moniker:
                moniker = coin.asset.get_monikers()[0]
                print "-" * 79
                print moniker
                print "-" * 79
            print ("%s %s:%s %s (%s) %s %s" % (
                    coin.get_address(), coin.txhash, coin.outindex,
                    coin.colorvalues[0], coin.value,
                    coin.is_confirmed(), coin.get_spending_txs()))

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

    @apigen.command()
    def p2porders(self):
        """Show peer to peer trade orders"""
        agent = self.init_p2ptrade()
        agent.update()
        for offer in agent.their_offers.values():
            print (offer.get_data())

    @apigen.command()
    def p2psell(self, moniker, amount, price, wait):
        """Sell asset/color for bitcoin via peer to peer trade."""
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(True, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent, wait)

    @apigen.command()
    def p2pbuy(self, moniker, amount, price, wait):
        """Buy asset/color for bitcoin via peer to peer trade."""
        agent = self.init_p2ptrade()
        offer = self.p2ptrade_make_offer(False, kwargs)
        agent.register_my_offer(offer)
        self.p2ptrade_wait(agent, wait)


if __name__ == "__main__":
    apigen.run(Ngccc)


