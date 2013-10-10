
class ColorDefinitionManager(object):
    def update(self):
        pass


class MempoolColorData(object):
    def __init__(self, blockchain_state):
        self.blockchain_state = blockchain_state
        self.txs = dict()
    def get(self, color_id, txhash, outindex):
        return None
    def has_tx(self, txhash):
        return False
    def get_any(self, txhash, outindex):
        return []
    def update(self):
        pass

class ColorData(object):
    pass

class ThickColorData(ColorData):
    def __init__(self, cdbuilder, mempoolcd, blockchain_state, colordefman, cdstore):
        self.cdbuilder = cdbuilder
        self.mempoolcd = mempoolcd
        self.blockchain_state = blockchain_state
        self.colordefman = colordefman
        self.cdstore = cdstore

    def resolve_color_id(self, color_id):
        return color_id

    def get(self, color_id, txhash, outindex):
        color_id = self.resolve_color_id(color_id)
        if self.mempoolcd.has_tx(txhash):
            return self.mempoolcd.get_any(txhash, outindex)
        else:
            return self.cdstore.get_any(txhash, outindex)

    def get_any(self, txhash, outindex):
        if self.mempoolcd.has_tx(txhash):
            return self.mempoolcd.get_any(txhash, outindex)
        else:
            return self.cdstore.get_any(txhash, outindex)
        
    def update(self):
        self.blockchain_state.update()
        self.colordefman.update()
        self.cdbuilder.update()
        self.mempoolcd.update()
        



class CAWallet(object):
    def update(self):
        pass

class ColoredCoinAgent(object):
    def __init__(self, blockchain_state, color_data, wallet):
        self.blockchain_state = blockchain_state
        self.color_data = color_data
        self.wallet = wallet

    def update(self):
        self.blockchain_state.update()
        self.color_data.update()
        self.wallet.update()
