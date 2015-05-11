"""
wallet_controller.py

Controls wallet model in a high level manner
Executes high level tasks such as get balance
"""

import os
from ngcccbase import sanitize
from collections import defaultdict
from decimal import Decimal
from asset import AssetTarget, AdditiveAssetValue
from coindb import CoinQuery
from pycoin.tx.Tx import Tx
from pycoin.serialize import b2h_rev
from ngcccbase import pycoin_txcons
from ngcccbase.p2ptrade.protocol_objects import MyEOffer
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.comm import HTTPComm
from coloredcoinlib.colordef import OBColorDefinition
from coloredcoinlib.colordef import EPOBCColorDefinition
from coloredcoinlib.colordef import InvalidColorError
from coloredcoinlib.colordef import UNCOLORED_MARKER
from coloredcoinlib import (InvalidColorDefinitionError, ColorDefinition,
                            GENESIS_OUTPUT_MARKER,
                            ColorTarget, SimpleColorValue)
from ngcccbase.coindb import ProvidedUTXO
from txcons import (BasicTxSpec, 
                    SimpleOperationalTxSpec, 
                    InputsProvidedOperationalTxSpec,
                    RawTxSpec)
from wallet_model import ColorSet
from ngcccbase.address import coloraddress_to_bitcoinaddress


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

    def _all_colorids_set(self):
        color_id_set = set()
        for asset in self.get_all_assets():
            color_id_set.update(asset.color_set.color_id_set)
        return color_id_set

    def get_tx(self, txid):
        return self.model.ccc.blockchain_state.get_tx(txid)

    def get_txout_coloridvalues(self, txid, outindex, color_id_set=None):
        if not color_id_set:
            color_id_set = self._all_colorids_set()
        colordata = self.model.ccc.colordata
        return colordata.get_colorvalues(color_id_set, txid, outindex)

    def get_txout_assetvalues(self, txid, outindex, asset=None):
        assets = [asset] if asset else self.get_all_assets()
        def getassetvalue(asset):
            color_id_set = asset.color_set.color_id_set
            values = self.get_txout_coloridvalues(txid, outindex, color_id_set)
            return (asset, sum(map(lambda v: v.get_value(), values)))
        return map(getassetvalue, assets)

    def _p2ptrade_wait(self, agent, wait):
        if wait and wait > 0:
            for _ in xrange(wait):
                agent.update()
                sleep(1)
        else:
            for _ in xrange(4*6):
                agent.update()
                sleep(0.25)

    def p2ptrade_make_offer(self, we_sell, asset, value, price, wait):
        total = int(Decimal(value)/Decimal(asset.unit)*Decimal(price))
        color_desc = asset.get_color_set().color_desc_list[0]
        sell_side = {"color_spec": color_desc, "value": value}
        buy_side = {"color_spec": "", "value": total}
        agent = self._p2ptrade_init_agent()
        if we_sell:
            agent.register_my_offer(MyEOffer(None, sell_side, buy_side))
        else:
            agent.register_my_offer(MyEOffer(None, buy_side, sell_side))
        self._p2ptrade_wait(agent, wait)

    def _p2ptrade_init_agent(self):
        ewctrl = EWalletController(self.model, self)
        config = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        comm = HTTPComm(config, 'http://p2ptrade.btx.udoidio.info/messages')
        return EAgent(ewctrl, config, comm)

    def p2porders(self, asset, sellonly, buyonly):

        # get offers
        agent = self._p2ptrade_init_agent()
        agent.update()
        offers = agent.their_offers.values()
        offers = map(lambda offer: offer.get_data(), offers)

        # filter asset if given
        if asset:
            descs = asset.get_color_set().color_desc_list
            def func(offer):
                return (offer["A"]["color_spec"] in descs or
                        offer["B"]["color_spec"] in descs)
            offers = filter(func, offers)

        # filter sellonly if given
        if sellonly:
            offers = filter(lambda o: o["A"]["color_spec"] != "", offers)

        # filter buyonly if given
        if buyonly:
            offers = filter(lambda o: o["A"]["color_spec"] == "", offers)

        return offers

    def publish_rawtx(self, rawtx):
        blockchain_state = self.model.ccc.blockchain_state
        return blockchain_state.publish_tx(rawtx)

    def publish_tx(self, signed_tx_spec):
        """Given a signed transaction <signed_tx_spec>, publish the transaction
        to the public bitcoin blockchain. Prints the transaction hash as a
        side effect. Returns the transaction hash.
        """
        txhex = signed_tx_spec.get_hex_tx_data()
        txhash = signed_tx_spec.get_hex_txhash()
        r_txhash = self.publish_rawtx(txhex)
        if r_txhash and (r_txhash != txhash) and not self.testing:
            raise Exception('Bitcoind reports different txhash!')

        if signed_tx_spec.composed_tx_spec:
            self.model.txdb.add_raw_tx(signed_tx_spec)
        # TODO add to history
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
    
    def get_utxos(self, asset, amount):
        tx_spec = SimpleOperationalTxSpec(self.model, None)
        color_id = asset.get_color_id()
        colordef = self.model.get_color_def(color_id)
        colorvalue = SimpleColorValue(colordef=colordef, value=amount)
        return tx_spec.select_coins(colorvalue)

    def createtx(self, utxos, targets, sign, publish):
        if not sign and publish:
            raise Exception("Cannot publish unsigned transaction!")

        otxs = InputsProvidedOperationalTxSpec(self.model, None)

        # add inputs
        for utxo in utxos:
            otxs.add_utxo(ProvidedUTXO(self, utxo))

        # add targets
        for target in targets:
            amount = target["amount"]
            address = coloraddress_to_bitcoinaddress(target["coloraddress"])
            color_id = target["asset"].get_color_id()
            colordef = self.model.get_color_def(color_id)
            colorvalue = SimpleColorValue(colordef=colordef, value=amount)
            otxs.add_target(ColorTarget(address, colorvalue))

        # transform tx
        ctxs = self.model.transform_tx_spec(otxs, 'composed')
        if sign:
            rtxs = self.model.transform_tx_spec(ctxs, 'signed')
            # TODO confirm all signed if allow partial flag not set
        else:
            rtxs = RawTxSpec.from_composed_tx_spec(self.model, ctxs)

        if publish:
            self.publish_tx(rtxs)
        return rtxs.get_hex_tx_data()

    def sign_rawtx(self, rawtx):
        tx = Tx.tx_from_hex(rawtx)
        def reformat(tx_in):
            return ProvidedUTXO(self, {
                'txid' : b2h_rev(tx_in.previous_hash),
                'outindex' : tx_in.previous_index
            })
        utxos = map(reformat, tx.txs_in)
        self.model.is_testnet()
        pycoin_txcons.sign_tx(tx, utxos, self.model.is_testnet())
        return tx.as_hex()

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
        return self.publish_tx(signed_tx_spec)

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
        return "foo"
        txid = self.publish_tx(signed_tx_spec)

        self.model.tx_history.add_send_entry(
            txid, asset, target_addrs, raw_colorvalues
        )
        return txid

    def get_address_record(self, bitcoinaddress):
        wam = self.model.get_address_manager()
        for address_record in wam.get_all_addresses():
            if bitcoinaddress == address_record.get_address():
                return address_record
        raise Exception("No address record for %s" % bitcoinaddress)
        return None

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
        unspent = self.model.make_coin_query({"asset": asset, "spent": False})
        spent = self.model.make_coin_query({"asset": asset, "spent": True})
        utxo_list = (unspent.get_result() + spent.get_result())
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
