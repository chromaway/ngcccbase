"""
wallet_controller.py

Controls wallet model in a high level manner
Executes high level tasks such as get balance
 (tasks that require more complex logic) [verification needed]
"""

from asset import AssetTarget, AdditiveAssetValue
from coloredcoinlib import (InvalidColorDefinitionError, ColorDefinition,
                            GENESIS_OUTPUT_MARKER,
                            ColorTarget, SimpleColorValue)
from wallet_model import ColorSet
from txcons import BasicTxSpec, SimpleOperationalTxSpec


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
        txhash = signed_tx_spec.get_hex_txhash()
        r_txhash = None
        bitcoind = self.model.ccc.blockchain_state.bitcoind
        try:
            r_txhash = bitcoind.sendrawtransaction(txhex)
        except Exception as e:                      # pragma: no cover
            print ("got error %s from bitcoind" % e)  # pragma: no cover
        
        if r_txhash and (r_txhash != txhash) and not self.testing:
            raise Exception('bitcoind reports different txhash')  # pragma: no cover
        
        if r_txhash is None:                                      # pragma: no cover
            # bitcoind did not eat our txn, check if it is mempool
            mempool = bitcoind.getrawmempool()                    # pragma: no cover
            if txhash not in mempool:                             # pragma: no cover
                raise Exception(                                  # pragma: no cover
                    "bitcoind didn't accept the transaction")     # pragma: no cover

        if signed_tx_spec.composed_tx_spec:
            self.model.txdb.add_signed_tx(txhash, signed_tx_spec)
            self.model.utxo_man.apply_tx(txhash, signed_tx_spec)
        return txhash

    def scan_utxos(self):
        """Updates all Unspent Transaction Outs for addresses associated with
        this wallet.
        """
        self.model.utxo_man.update_all()

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
        # scan the tx so that the rest of the system knows
        self.model.ccc.colordata.cdbuilder_manager.scan_txhash(
            asset.color_set.color_id_set, txhash)

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
        height = self.model.ccc.blockchain_state.bitcoind.getblockcount() \
            - 1
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

    def get_address_balance(self, asset):
        """Returns an integer value corresponding to the total number
        of Satoshis owned of asset/color <asset>.
        """
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        ars = self.get_all_addresses(asset)
        addresses = [ar.get_address() for ar in ars]
        retval = [{'address': ar.get_address(),
                   'color_address': ar.get_color_address(),
                   'value': 0} for ar in ars]
        for utxo in utxo_list:
            i = addresses.index(utxo.address_rec.get_address())
            retval[i]['value'] += asset.get_colorvalue(utxo).get_value()
        return retval

    def get_balance(self, asset):
        """Returns an integer value corresponding to the total number
        of Satoshis owned of asset/color <asset>.
        """
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        value_list = [asset.get_colorvalue(utxo) for utxo in utxo_list]
        if len(value_list) == 0:
            return 0
        else:
            return SimpleColorValue.sum(value_list).get_value()

    def get_history(self, asset):
        """Returns the history of an asset for all addresses of that color
        in this wallet
        """
        # update everything first
        self.get_balance(asset)
        return self.model.get_history_for_asset(asset)
