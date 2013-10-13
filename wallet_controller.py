

class WalletController(object):
    def __init__(self, model):
        self.model = model

    def get_new_address(self, asset):
        wam = self.model.get_address_manager()
        return wam.get_new_address(asset.get_color_set())

    def add_asset_definition(self, params):
        self.model.get_asset_definition_manager().add_asset_definition(params)

    def get_balance(self, asset):
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        value_list = [asset.get_utxo_value(utxo) for utxo in utxo_list]
        return sum(value_list)
