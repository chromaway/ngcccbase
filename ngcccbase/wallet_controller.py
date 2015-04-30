"""
wallet_controller.py

Controls wallet model in a high level manner
Executes high level tasks such as get balance
"""

import os
import csv
from collections import defaultdict
from decimal import Decimal
from asset import AssetTarget, AdditiveAssetValue
from coindb import CoinQuery
from coloredcoinlib.colordef import OBColorDefinition
from coloredcoinlib.colordef import EPOBCColorDefinition
from coloredcoinlib.colordef import InvalidColorError
from coloredcoinlib.colordef import UNCOLORED_MARKER
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
        self.testing = False

    def publish_tx(self, signed_tx_spec):
        """Given a signed transaction <signed_tx_spec>, publish the transaction
        to the public bitcoin blockchain. Prints the transaction hash as a
        side effect. Returns the transaction hash.
        """
        txhex = signed_tx_spec.get_hex_tx_data()
        txhash = signed_tx_spec.get_hex_txhash()
        r_txhash = None
        blockchain_state = self.model.ccc.blockchain_state
        try:
            r_txhash = blockchain_state.publish_tx(txhex)
        except Exception as e:
            pass

        if r_txhash and (r_txhash != txhash) and not self.testing:
            raise Exception('Bitcoind reports different txhash!')

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
        self.model.tx_history.entries.clear()
        self.model.tx_history.populate_history()

    def scan_utxos(self):
        self.model.utxo_fetcher.scan_all_addresses()

    def sanitize_csv_input(self, csvvalues, row): # FIXME move to api sanitizer
        adm = self.model.get_asset_definition_manager()

        # must have three entries
        if len(csvvalues) != 3:
            msg = ("CSV entry must have three values 'moniker,address,value'. "
                   "Row %s has %s values!")
            raise Exception(msg % (row, len(csvvalues)))
        moniker, target_addr, value = csvvalues

        # asset must exist
        asset = adm.get_asset_by_moniker(moniker)
        if not asset:
            msg = "Asset '%s' in row %s not found!"
            raise Exception(msg % (moniker, row))

        # asset must match address asset
        address_asset, address = adm.get_asset_and_address(target_addr)
        if asset != address_asset:
            msg = "Address and asset don't match in row: %s!"
            raise AssetMismatchError(msg % row)

        # check if valid address
        if not self.model.validate_address(address):
            msg = "Address %s in row: %s is not valid!"
            raise Exception(msg % (target_addr, row))

        # make sure value is a number
        try:
            value = Decimal(value)
        except:
            msg = "Value '%s' in row %s is not a number.!"
            raise Exception(msg % (value, row))

        # value must be positive
        if value < Decimal("0"):
            msg = "Value '%s' in row %s not > 0.!"
            raise Exception(msg % (value, row))

        # check if valid amount for asset
        if not asset.validate_value(value):
            msg = "Value '%s' in row %s is not a multiple of %s.!"
            raise Exception(msg % (value, row, asset.get_atom()))

        # convert to amount to satoshis
        value = asset.parse_value(value)

        return asset, address, value

    def sendmany_sums(self, entries):
        sums = defaultdict(Decimal)
        for asset, address, value in entries:
            sums[asset] += value
        return sums

    def validate_sendmany_entries(self, entries):
        # TODO check for max entries
        sums = self.sendmany_sums(entries)

        # check if required asset amount available
        for asset, amount in sums.items():
            available = Decimal(self.get_available_balance(asset))
            if amount > available:
                msg = ("Requred amount of %(value)s %(moniker)s exceeds your "
                       "available balance of %(available)s %(moniker)s!") % {
                    'moniker' : asset.get_monikers()[0],
                    'value' : asset.format_value(amount),
                    'available' : asset.format_value(available),
                }
                raise Exception(msg)

        # check inputs are only obc or only epobc
        def reduce_function(a, b):
            adef = a.get_color_def()
            bdef = b.get_color_def()
            if adef == UNCOLORED_MARKER:
                return b
            if bdef == UNCOLORED_MARKER:
                return a
            a_is_obc = isinstance(adef, OBColorDefinition)
            b_is_obc = isinstance(bdef, OBColorDefinition)
            a_is_epobc = isinstance(adef, EPOBCColorDefinition)
            b_is_epobc = isinstance(bdef, EPOBCColorDefinition)
            if a_is_obc and b_is_obc:
                return a
            elif a_is_epobc and b_is_epobc:
                return a
            raise InvalidColorError("Colortype miss match for %s and %s!" % (
                a.get_monikers()[0], b.get_monikers()[0]
            ))
        reduce(reduce_function, sums.keys())

    def parse_sendmany_csv(self, csv_file_path):
        """Send amounts in csv file with format 'moniker,address,value'"""
        entries = []
        with open(csv_file_path, 'rb') as csvfile:
            for index, csvvalues in enumerate(csv.reader(csvfile)):
                entries.append(self.sanitize_csv_input(csvvalues, index + 1))
        return entries

    def sendmany_coins(self, entries):
        """Sendmany coins given in entries [(asset, address, value), ...] """
        self.validate_sendmany_entries(entries)
        tx_spec = SimpleOperationalTxSpec(self.model, None)
        for asset, address, value in entries:
            color_id = asset.get_color_id()
            colordef = self.model.get_color_def(color_id)
            colorvalue = SimpleColorValue(colordef=colordef, value=value)
            tx_spec.add_target(ColorTarget(address, colorvalue))
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        txhash = self.publish_tx(signed_tx_spec)
        # TODO add to history
        return txhash

    def send_coins(self, asset, target_addrs, raw_colorvalues):
        """Sends coins to address <target_addr> of asset/color <asset>
        of amount <colorvalue> Satoshis.
        """
        tx_spec = BasicTxSpec(self.model)
        adm = self.model.get_asset_definition_manager()
        for target_addr, raw_colorvalue in zip(target_addrs, raw_colorvalues):
            # decode the address
            address_asset, address = adm.get_asset_and_address(target_addr)
            if asset != address_asset:
                msg = "Address and asset don't match: %s %s!"
                raise AssetMismatchError(msg % (asset, address_asset))
            assettarget = AssetTarget(address,
                                      AdditiveAssetValue(asset=asset,
                                                         value=raw_colorvalue))
            tx_spec.add_target(assettarget)
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        txhash = self.publish_tx(signed_tx_spec)

        self.model.tx_history.add_send_entry(
            txhash, asset, target_addrs, raw_colorvalues
        )
        return txhash

    def issue_coins(self, moniker, pck, units, atoms_in_unit):
        """Issues a new color of name <moniker> using coloring scheme
        <pck> with <units> per share and <atoms_in_unit> total.
        """

        color_definition_cls = ColorDefinition.get_color_def_cls_for_code(pck)
        if not color_definition_cls:
            msg = 'Color scheme "%s" not recognized'
            raise InvalidColorDefinitionError(msg % pck)

        total = int(units * atoms_in_unit)
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
