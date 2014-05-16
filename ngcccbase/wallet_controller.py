"""
wallet_controller.py

Controls wallet model in a high level manner
Executes high level tasks such as get balance
"""

from asset import AssetTarget, AdditiveAssetValue
from coindb import CoinQuery
from coloredcoinlib import (InvalidColorDefinitionError, ColorDefinition,
                            GENESIS_OUTPUT_MARKER,
                            ColorTarget, SimpleColorValue)
from txcons import BasicTxSpec, SimpleOperationalTxSpec
from wallet_model import ColorSet


class AssetMismatchError(Exception):
    pass


class WalletController(object):
    """Controller for a wallet. Used for executing tasks related to the wallet.
    """
    def __init__(self, model):
        """Given a wallet model <model>, create a wallet controller.
        """
        self.model = model
        self.debug = False
        self.testing = False

    def publish_tx(self, signed_tx_spec):
        """Given a signed transaction <signed_tx_spec>, publish the transaction
        to the public bitcoin blockchain. Prints the transaction hash as a
        side effect. Returns the transaction hash.
        """
        txhex = signed_tx_spec.get_hex_tx_data()
        print txhex
        txhash = signed_tx_spec.get_hex_txhash()
        r_txhash = None
        blockchain_state = self.model.ccc.blockchain_state
        try:
            r_txhash = blockchain_state.publish_tx(txhex)
        except Exception as e:                      # pragma: no cover
            print ("got error %s from bitcoind" % e)  # pragma: no cover
        
        if r_txhash and (r_txhash != txhash) and not self.testing:
            raise Exception('bitcoind reports different txhash')  # pragma: no cover
        
        """if r_txhash is None:                                      # pragma: no cover
            # bitcoind did not eat our txn, check if it is mempool
            mempool = bitcoind.getrawmempool()                    # pragma: no cover
            if txhash not in mempool:                             # pragma: no cover
                raise Exception(                                  # pragma: no cover
                    "bitcoind didn't accept the transaction")     # pragma: no cover"""

        if signed_tx_spec.composed_tx_spec:
            self.model.txdb.add_raw_tx(signed_tx_spec)
        return txhash

    def full_rescan(self):
        """Updates all Unspent Transaction Outs for addresses associated with
        this wallet."""
        self.model.get_coin_manager().purge_coins()
        self.model.get_tx_db().purge_tx_db()
        wam = self.model.get_address_manager()
        bc_interface = self.model.utxo_fetcher.interface
        tx_hashes = []
        for ar in wam.get_all_addresses():
            tx_hashes.extend(bc_interface.get_address_history(ar.get_address()))
        sorted_txs = self.model.get_blockchain_state().sort_txs(tx_hashes)
        txdb = self.model.get_tx_db()
        for tx in sorted_txs:
            txdb.add_tx_by_hash(tx.hash)
        self.model.tx_history.populate_history()

    def scan_utxos(self):
        self.model.utxo_fetcher.scan_all_addresses()

    def send_coins(self, asset, target_addrs, raw_colorvalues):
        """Sends coins to address <target_addr> of asset/color <asset>
        of amount <colorvalue> Satoshis.
        """
        tx_spec = BasicTxSpec(self.model)
        adm = self.model.get_asset_definition_manager()
        colormap = self.model.get_color_map()
        for target_addr, raw_colorvalue in zip(target_addrs, raw_colorvalues):
            # decode the address
            address_asset, address = adm.get_asset_and_address(target_addr)
            if asset != address_asset:
                raise AssetMismatchError("Address and asset don't match: %s %s" %
                                         (asset, address_asset))
            assettarget = AssetTarget(address,
                                      AdditiveAssetValue(asset=asset,
                                                         value=raw_colorvalue))
            tx_spec.add_target(assettarget)
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        if self.debug:
            print ("In:")
            for txin in signed_tx_spec.composed_tx_spec.txins:
                print (txin.prevout)
            print ("Out:")
            for txout in signed_tx_spec.composed_tx_spec.txouts:
                print (txout.value)
        txhash = self.publish_tx(signed_tx_spec)
        self.model.tx_history.add_send_entry(txhash, asset, 
                                             target_addrs, raw_colorvalues)

    def issue_coins(self, moniker, pck, units, atoms_in_unit):
        """Issues a new color of name <moniker> using coloring scheme
        <pck> with <units> per share and <atoms_in_unit> total.
        """

        color_definition_cls = ColorDefinition.get_color_def_cls_for_code(pck)
        if not color_definition_cls:
            raise InvalidColorDefinitionError('color scheme %s not recognized' % pck)

        total = units * atoms_in_unit
        op_tx_spec = SimpleOperationalTxSpec(self.model, None)
        wam = self.model.get_address_manager()
        address = wam.get_new_genesis_address()
        colorvalue = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER,
                                      value=total)
        color_target = ColorTarget(address.get_address(), colorvalue)
        op_tx_spec.add_target(color_target)
        genesis_ctxs = color_definition_cls.compose_genesis_tx_spec(op_tx_spec)
        genesis_tx = self.model.transform_tx_spec(genesis_ctxs, 'signed')
        height = self.model.ccc.blockchain_state.get_block_count() - 1
        genesis_tx_hash = self.publish_tx(genesis_tx)
        color_desc = ':'.join([pck, genesis_tx_hash, '0', str(height)])
        adm = self.model.get_asset_definition_manager()
        asset = adm.add_asset_definition({"monikers": [moniker],
                                          "color_set": [color_desc],
                                          "unit": atoms_in_unit})
        wam.update_genesis_address(address, asset.get_color_set())

        # scan the tx so that the rest of the system knows
        self.model.ccc.colordata.cdbuilder_manager.scan_txhash(
            asset.color_set.color_id_set, genesis_tx_hash)

    def get_new_address(self, asset):
        """Given an asset/color <asset>, create a new bitcoin address
        that can receive it. Returns the AddressRecord object.
        """
        wam = self.model.get_address_manager()
        return wam.get_new_address(asset)

    def get_all_addresses(self, asset):
        """Given an asset/color <asset>, return a list of AddressRecord
        objects that correspond in this wallet.
        """
        wam = self.model.get_address_manager()
        return wam.get_addresses_for_color_set(asset.get_color_set())

    def get_all_assets(self):
        """Return all assets that are currently registered
        """
        adm = self.model.get_asset_definition_manager()
        return adm.get_all_assets()

    def add_asset_definition(self, params):
        """Imports an asset/color with the params <params>.
        The params consist of:
        monikers - List of color names (e.g. "red")
        color_set - List of color definitions (e.g. "obc:f0b...d565:0:128649")
        """
        self.model.get_asset_definition_manager().add_asset_definition(params)

    def get_received_by_address(self, asset):
        utxo_list = \
            (self.model.make_coin_query({"asset": asset, "spent": False}).get_result()
             +
             self.model.make_coin_query({"asset": asset, "spent": True}).get_result())
        ars = self.get_all_addresses(asset)
        addresses = [ar.get_address() for ar in ars]
        retval = [{'address': ar.get_address(),
                   'color_address': ar.get_color_address(),
                   'value': asset.get_null_colorvalue()} for ar in ars]
        for utxo in utxo_list:
            i = addresses.index(utxo.address_rec.get_address())
            retval[i]['value'] += asset.get_colorvalue(utxo)
        return retval

    def get_coinlog(self):
        coinlog = []
        for asset in self.get_all_assets():
            query_1 = CoinQuery(self.model, asset.get_color_set(),
                                {'spent': True, 'include_unconfirmed': True})
            query_2 = CoinQuery(self.model, asset.get_color_set(),
                                {'spent': False, 'include_unconfirmed': True})
            for address in self.get_all_addresses(asset):
                for coin in query_1.get_coins_for_address(address):
                    coin.asset = asset
                    coin.address_rec = address
                    coinlog.append(coin)
                for coin in query_2.get_coins_for_address(address):
                    coin.asset = asset
                    coin.address_rec = address
                    coinlog.append(coin)
        return coinlog

    def _get_balance(self, asset, options):
        """Returns an integer value corresponding to the total number
        of Satoshis owned of asset/color <asset>.
        """
        query = {"asset": asset}
        query.update(options)
        cq = self.model.make_coin_query(query)
        utxo_list = cq.get_result()
        value_list = [asset.get_colorvalue(utxo) for utxo in utxo_list]
        if len(value_list) == 0:
            return 0
        else:
            return SimpleColorValue.sum(value_list).get_value()

    def get_available_balance(self, asset):
        return self._get_balance(asset, {"spent": False})
    
    def get_total_balance(self, asset):
        return self._get_balance(asset, {"spent": False, 
                                        "include_unconfirmed": True})

    def get_unconfirmed_balance(self, asset):
        return self._get_balance(asset, {"spent": False, 
                                        "only_unconfirmed": True})
    

    def get_history(self, asset):
        """Returns the history of an asset for all addresses of that color
        in this wallet
        """
        # update everything first
        self.get_available_balance(asset)
        return self.model.get_history_for_asset(asset)
