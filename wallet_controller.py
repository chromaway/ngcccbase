# Controls wallet model in a high level manner
# Executes high level tasks such as get balance (tasks that require more complex logic)
# [verification needed]
class WalletController(object):
    def __init__(self, model):
        self.model = model

    def send_coins(self, target_addr, asset, value):
        txcon = self.model.make_transaction_constructor()
        txcon.addTarget(target_addr, asset, value)
        txcon.constructTx()
        txhex = txcon.getTxDataHex()
        print txhex
        self.model.ccc.blockchain_state.bitcoind.sendrawtransaction(txhex)
        

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
