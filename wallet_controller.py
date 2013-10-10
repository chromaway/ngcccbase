

class WalletController(object):
    def __init__(self, model):
        self.model = model

    def get_balance(self, asset):
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()
        value_list = [asset.get_utxo_value(utxo) for utxo in utxo_list]
        return sum(value_list)
