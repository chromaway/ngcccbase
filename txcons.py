# transaction constructors

def pycoin_construct_tx(input_utxos, outputs):
    from pycoin import encoding
    from pycoin.tx import UnsignedTx, SecretExponentSolver
    import io
    inputs = [utxo.get_pycoin_coin_source() for utxo in input_utxos]
    secret_exponents = [encoding.wif_to_secret_exponent(utxo.address.meat.privkey)
                        for utxo in input_utxos]
    unsigned_tx = UnsignedTx.standard_tx(inputs, outputs)
    solver = SecretExponentSolver(secret_exponents)
    new_tx = unsigned_tx.sign(solver)
    s = io.BytesIO()
    new_tx.stream(s)
    return s.getvalue()


class AbstractTC(object):
    def __init__(self, model):
        self.model = model
        self.targets = []
        self.fee = 10000
        self.tx_data = None
    def setFee(self, fee):
        self.fee = fee
    def addTarget(self, target_addr, asset, value):
        self.targets.append((target_addr, asset, value))
    def constructTx(self):
        raise Exception('not implemented')
    def getTxData(self):
        return self.tx_data
    def getTxDataHex(self):
        import binascii
        return binascii.hexlify(self.getTxData()).decode('utf8')

    
class MonoassetTC(AbstractTC):
    def __init__(self, model, asset):
        super(MonoassetTC, self).__init__(model)
        self.asset = asset
    def addTarget(self, target_addr, asset, value):
        if asset != self.asset:
            raise Exception('TC cannot accept target with this asset')
        super(MonoassetTC, self).addTarget(target_addr, asset, value)


class UncoloredTC(MonoassetTC):
    def selectCoins(self, utxo_list, tsum):
        ssum = 0
        selection = []
        if tsum == 0:
            raise Exception('cannot select 0 coins')
        for utxo in utxo_list:
            ssum += utxo.value
            selection.append(utxo)
            if ssum >= tsum:
                return selection, ssum
        raise Exception('not enough coins to reach the target')
    
    def getChangeAddress(self, asset):
        wam = self.model.get_address_manager()
        return wam.get_new_address(asset.get_color_set())
    def constructTx(self):
        cq = self.model.make_coin_query({"asset": self.asset})
        utxo_list = cq.get_result()
        ttotal = sum([target[2] for target in self.targets])
        fee = self.fee
        sel_utxos, sum_sel_coins = self.selectCoins(utxo_list, ttotal + fee)
        change = sum_sel_coins - ttotal - fee
        outputs = [(target[2], target[0]) for target in self.targets]
        if change > 0:
           outputs.append((change, self.getChangeAddress(self.asset).get_address()))
        self.tx_data = pycoin_construct_tx(sel_utxos, outputs)

class MonocolorTC(MonoassetTC):
    pass


class GenericTC(AbstractTC):
    def addTarget(self, target_addr, asset, value):
        from wallet_model import AssetDefinition
        if not isinstance(asset, AssetDefinition):
            raise Exception("asset definition is expected in GenericTC.addTarget")
        if len(self.targets)>0:
            raise Exception("currently GenericTC supports only one target")
        self.targets.append((target_addr, asset, value))
    def constructTx(self):
        if len(self.targets) != 1:
            raise Exception("GenericTC requires exactly one target")
        target = self.targets[0]
        asset = target[1]
        self.txc = asset.make_transaction_constructor()
        self.txc.addTarget(target[0], target[1], target[2])
        self.txc.constructTx()
    def getTxData(self):
        return self.txc.getTxData()
