"""
wallet_controller.py

Controls wallet model in a high level manner
Executes high level tasks such as get balance
 (tasks that require more complex logic) [verification needed]
"""

from coloredcoinlib.colordef import ColorDefinition, GENESIS_OUTPUT_MARKER
from wallet_model import ColorSet
from txcons import BasicTxSpec, SimpleOperationalTxSpec


class WalletController(object):
    """Controller for a wallet. Used for executing tasks related to the wallet.
    """
    def __init__(self, model):
        """Given a wallet model <model>, create a wallet controller.
        """
        self.model = model
        self.debug = False

    def publish_tx(self, signed_tx_spec):
        """Given a signed transaction <signed_tx_spec>, publish the transaction
        to the public bitcoin blockchain. Prints the transaction hash as a
        side effect. Returns the transaction hash.
        """
        txhex = signed_tx_spec.get_hex_tx_data()
        print txhex
        txhash = self.model.ccc.blockchain_state.bitcoind.sendrawtransaction(
            txhex)
        if signed_tx_spec.composed_tx_spec:
            self.model.txdb.add_signed_tx(txhash, signed_tx_spec)

        # delete the spent utxo from the db
        for txin in signed_tx_spec.composed_tx_spec.txins:
            self.model.utxo_man.store.del_utxo(txin.utxo.txhash,
                                               txin.utxo.outindex)

        # put the new utxo into the db
        for i, txout in enumerate(signed_tx_spec.composed_tx_spec.txouts):
            script = signed_tx_spec.pycoin_tx.txs_out[i].script.encode('hex')
            self.model.utxo_man.store.add_utxo(txout.target_addr, txhash, i,
                                               txout.value, script)
        return txhash

    def scan_utxos(self):
        """Updates all Unspent Transaction Outs for addresses associated with
        this wallet.
        """
        self.model.utxo_man.update_all()

    def send_coins(self, asset, target_addrs, colorvalues):
        """Sends coins to address <target_addr> of asset/color <asset>
        of amount <colorvalue> Satoshis.
        """
        tx_spec = BasicTxSpec(self.model)
        for target_addr, colorvalue in zip(target_addrs, colorvalues):
            tx_spec.add_target(target_addr, asset, colorvalue)
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        if self.debug:
            print "In:"
            for txin in signed_tx_spec.composed_tx_spec.txins:
                print txin.utxo.value
            print "Out:"
            for txout in signed_tx_spec.composed_tx_spec.txouts:
                print txout.value
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
            raise Exception('color scheme %s not recognized' % pck)

        total = units * atoms_in_unit
        op_tx_spec = SimpleOperationalTxSpec(self.model, None)
        wam = self.model.get_address_manager()
        address = wam.get_new_genesis_address()
        op_tx_spec.add_target(
            address.get_address(), GENESIS_OUTPUT_MARKER, total)
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
        addresses = [ar.get_address() for ar in self.get_all_addresses(asset)]
        retval = [{'address': a, 'value': 0} for a in addresses]
        for utxo in utxo_list:
            i = addresses.index(utxo.address_rec.get_address())
            retval[i]['value'] += asset.get_colorvalue(utxo)
        return retval

    def get_balance(self, asset):
        """Returns an integer value corresponding to the total number
        of Satoshis owned of asset/color <asset>.
        """
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        value_list = [asset.get_colorvalue(utxo) for utxo in utxo_list]
        return sum(value_list)

    def get_history(self, asset):
        """Returns the history of an asset for all addresses of that color
        in this wallet
        """
        # update everything first
        self.get_balance(asset)
        return self.model.get_history_for_asset(asset)
