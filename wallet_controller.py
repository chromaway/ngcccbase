# wallet_controller.py
#
# Controls wallet model in a high level manner
# Executes high level tasks such as get balance
#  (tasks that require more complex logic) [verification needed]

from coloredcoinlib.colordef import OBColorDefinition
from wallet_model import ColorSet
from txcons import BasicTxSpec, SimpleOperationalTxSpec


class WalletController(object):
    """Controller for a wallet. Used for executing tasks related to the wallet.
    """
    def __init__(self, model):
        """Given a wallet model <model>, create a wallet controller.
        """
        self.model = model

    def publish_tx(self, signed_tx_spec):
        """Given a signed transaction <signed_tx_spec>, publish the transaction
        to the public bitcoin blockchain. Prints the transaction hash as a
        side effect. Returns the transaction hash.
        """
        txhex = signed_tx_spec.get_hex_tx_data()
        print txhex
        txhash = self.model.ccc.blockchain_state.bitcoind.sendrawtransaction(
            txhex)
        self.model.txdb.add_signed_tx(txhash, signed_tx_spec)
        return txhash

    def scan_utxos(self):
        """Updates all Unspent Transaction Outs for addresses associated with
        this wallet.
        """
        self.model.utxo_man.update_all()

    def send_coins(self, target_addr, asset, value):
        """Sends coins to address <target_addr> of asset/color <asset>
        of amount <value> Satoshis.
        """
        tx_spec = BasicTxSpec(self.model)
        tx_spec.add_target(target_addr, asset, value)
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        self.publish_tx(signed_tx_spec)

    def issue_coins(self, moniker, pck, units, atoms_in_unit):
        """Issues a new color of name <moniker> using coloring scheme
        <pck> with <units> per share and <atoms_in_unit> total.
        """

        if pck == 'obc':
            total = units * atoms_in_unit
            op_tx_spec = SimpleOperationalTxSpec(self.model, None)
            wam = self.model.get_address_manager()
            addr = wam.get_new_genesis_address()
            op_tx_spec.add_target(addr.get_address(), -1, total)
            genesis_ctxs = OBColorDefinition.compose_genesis_tx_spec(
                op_tx_spec)
            genesis_tx = self.model.transform_tx_spec(genesis_ctxs, 'signed')
            height = self.model.ccc.blockchain_state.bitcoind.getblockcount() \
                - 1
            genesis_tx_hash = self.publish_tx(genesis_tx)
            color_desc = ':'.join(['obc', genesis_tx_hash, '0', str(height)])
            adm = self.model.get_asset_definition_manager()
            assdef = adm.add_asset_definition({"monikers": [moniker],
                                               "color_set": [color_desc],
                                               "unit": atoms_in_unit})
            wam.update_genesis_address(assdef.get_color_set())
        else:
            raise Exception('color scheme not recognized')

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

    def get_balance(self, asset):
        """Returns an integer value corresponding to the total number
        of Satoshis owned of asset/color <asset>.
        """
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        value_list = [asset.get_utxo_value(utxo) for utxo in utxo_list]
        return sum(value_list)
