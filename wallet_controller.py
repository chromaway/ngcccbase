# Controls wallet model in a high level manner
# Executes high level tasks such as get balance (tasks that require more complex logic)
# [verification needed]

import txcons

class WalletController(object):
    def __init__(self, model):
        self.model = model

    def publish_tx(self, signed_tx_spec):
        txhex = signed_tx_spec.get_hex_tx_data()
        print txhex
        txhash = self.model.ccc.blockchain_state.bitcoind.sendrawtransaction(txhex)
        self.model.txdb.add_tx(txhash, txhex)
        return txhash

    def scan_utxos(self):
        self.model.utxo_man.update_all()

    def send_coins(self, target_addr, asset, value):
        tx_spec = txcons.BasicTxSpec(self.model)
        tx_spec.add_target(target_addr, asset, value)
        signed_tx_spec = self.model.transform_tx_spec(tx_spec, 'signed')
        self.publish_tx(signed_tx_spec)
    
    def issue_coins(self, moniker, pck, units, atoms_in_unit):
        from coloredcoinlib.colordef import OBColorDefinition
        from wallet_model import ColorSet

        if pck == 'obc':
            total = units * atoms_in_unit
            op_tx_spec = txcons.SimpleOperationalTxSpec(self.model, None)
            wam = self.model.get_address_manager()
            addr = wam.get_new_address(ColorSet(self.model, []))
            op_tx_spec.add_target(addr.get_address(), -1, total)
            genesis_ctxs = OBColorDefinition.compose_genesis_tx_spec(op_tx_spec)
            genesis_tx = self.model.transform_tx_spec(genesis_ctxs, 'signed')
            height = self.model.ccc.blockchain_state.bitcoind.getblockcount() - 1
            genesis_tx_hash = self.publish_tx(genesis_tx)
            color_desc = ':'.join(['obc', genesis_tx_hash, '0', str(height)])
            adm = self.model.get_asset_definition_manager()
            assdef = adm.add_asset_definition({"monikers": [moniker],
                                               "color_set": [color_desc],
                                               "unit": atoms_in_unit})
            addr.color_set = assdef.get_color_set()
            wam.update_config()                                      
        else:
            raise Exception('color scheme not recognized')

    def get_new_address(self, asset):
        wam = self.model.get_address_manager()
        return wam.get_new_address(asset.get_color_set())

    def get_all_addresses(self, asset):
        wam = self.model.get_address_manager()
        return wam.get_addresses_for_color_set(asset.get_color_set())

    def add_asset_definition(self, params):
        self.model.get_asset_definition_manager().add_asset_definition(params)

    def get_balance(self, asset):
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        value_list = [asset.get_utxo_value(utxo) for utxo in utxo_list]
        return sum(value_list)
