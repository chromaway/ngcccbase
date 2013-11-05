# transaction constructors

from coloredcoinlib import txspec

class SimpleOperationalTxSpec(txspec.OperationalTxSpec):
    """subclass of OperationalTxSpec which uses wallet model"""
    def __init__(self, model, asset):
        super(SimpleOperationalTxSpec, self).__init__()
        self.model = model
        self.targets = []
        self.asset = asset

    def add_target(self, target_addr, color_id, colorvalue):
        self.targets.append((target_addr, color_id, colorvalue))

    def get_targets(self):
        return self.targets

    def get_change_addr(self, color_id):
        from wallet_model import ColorSet
        wam = self.model.get_address_manager()
        color_set = None
        if color_id == 0:
            color_set = ColorSet.from_color_ids(self.model, [0])
        elif self.asset.get_color_set().has_color_id(color_id):
            color_set = self.asset.get_color_set()
        if color_set == None:
            raise Exception('wrong color id')
        aw = wam.get_change_address(color_set)
        return aw.get_address()

    def select_coins(self, color_id, value):
        if not ((color_id == 0) or self.asset.get_color_set().has_color_id(color_id)):
            raise Exception("wrong color id requested")
        color_id_set = set([color_id])
        cq = self.model.make_coin_query({"color_id_set": color_id_set})
        utxo_list = cq.get_result()

        ssum = 0
        selection = []
        if value == 0:
            raise Exception('cannot select 0 coins')
        for utxo in utxo_list:
            ssum += utxo.value
            selection.append(utxo)
            if ssum >= value:
                return selection, ssum
        raise Exception('not enough coins to reach the target')

    def get_required_fee(self, tx_size):
        return 10000 # TODO


class BasicTxSpec(object):
    def __init__(self, model):
        self.model = model
        self.targets = []

    def add_target(self, target_addr, asset, value):
        self.targets.append((target_addr, asset, value))

    def is_monoasset(self):
        if not self.targets:
            raise Exception('basic txs is empty')
        asset = self.targets[0][1]
        for target in self.targets:
            if target[1] != asset:
                return False
        return True
    
    def is_monocolor(self):
        if not self.is_monoasset():
            return False
        asset = self.targets[0][1]
        return len(asset.get_color_set().color_id_set) == 1

    def is_uncolored(self):
        if not self.is_monoasset():
            return False
        asset = self.targets[0][1]
        return asset.get_color_list().color_id_set == set([0])


def pycoin_construct_tx(input_utxos, outputs, testnet):
    from pycoin import encoding
    from pycoin.tx import UnsignedTx, SecretExponentSolver
    import io
    inputs = [utxo.get_pycoin_coin_source() for utxo in input_utxos]
    secret_exponents = [encoding.wif_to_tuple_of_secret_exponent_compressed(utxo.address_rec.meat.privkey, is_test=testnet)[0]
                        for utxo in input_utxos]
    unsigned_tx = UnsignedTx.standard_tx(inputs, outputs, is_test=testnet)
    solver = SecretExponentSolver(secret_exponents)
    new_tx = unsigned_tx.sign(solver)
    s = io.BytesIO()
    new_tx.stream(s)
    return s.getvalue()


class SignedTxSpec(object):
    def __init__(self, model, composed_tx_spec, testnet):
        self.model = model
        self.testnet = testnet
        self.composed_tx_spec = composed_tx_spec
        self.construct_tx()

    def construct_tx(self):
        input_utxos = [txin.utxo 
                       for txin in self.composed_tx_spec.get_txins()]
        outputs = [(txout.value, txout.target_addr)
                   for txout in self.composed_tx_spec.get_txouts()]
        self.tx_data = pycoin_construct_tx(input_utxos, outputs, self.testnet)

    def get_tx_data(self):
        return self.tx_data

    def get_hex_tx_data(self):
        import binascii
        return binascii.hexlify(self.tx_data).decode("utf8")


def compose_uncolored_tx_spec(tx_spec):
    targets = tx_spec.get_targets()
    ttotal = sum([target[2] for target in targets])
    fee = tx_spec.get_required_fee(500)
    sel_utxos, sum_sel_coins = tx_spec.select_coins(0, ttotal + fee)
    txins = [txspec.ComposedTxSpec.TxIn(utxo) for utxo in sel_utxos]
    change = sum_sel_coins - ttotal - fee
    txouts = [txspec.ComposedTxSpec.TxOut(target[2], target[0]) for target in targets]
    if change > 0:
        outputs.append(txspec.ComposedTxSpec.TxOut(change, tx_spec.get_change_address(0)))
    return txspec.ComposedTxSpec(txins, txouts)


class TransactionSpecTransformer(object):
    """knows how to transform one kind of transaction spec into another"""

    def __init__(self, model, config):
        self.model = model
        self.testnet = config.get('testnet', False)

    def classify_tx_spec(self, tx_spec):
        if isinstance(tx_spec, BasicTxSpec):
            return 'basic'
        elif isinstance(tx_spec, txspec.OperationalTxSpec):
            return 'operational'
        elif isinstance(tx_spec, txspec.ComposedTxSpec):
            return 'composed'
        elif isinstance(tx_spec, SignedTxSpec):
            return 'signed'
        else:
            return None

    def transform_basic(self, tx_spec, target_spec_kind):
        if target_spec_kind in ['operational', 'composed', 'signed']:
            if tx_spec.is_monoasset():
                asset = tx_spec.targets[0][1]
                operational_ts = asset.make_operational_tx_spec(tx_spec)
                return self.transform(operational_ts, target_spec_kind)
        raise Exception('do not know how to transform tx spec')

    def transform_operational(self, tx_spec, target_spec_kind):
        if target_spec_kind in ['composed', 'signed']:
            if tx_spec.is_monocolor():
                color_id = tx_spec.get_targets()[0][1]
                if color_id == 0:
                    composed = compose_uncolored_tx_spec(tx_spec)
                else:
                    color_def = self.model.get_color_map().get_color_def(color_id)
                    composed = color_def.compose_tx_spec(tx_spec)
                return self.transform(composed, target_spec_kind)
        raise Exception('do not know how to transform tx spec')
        
    def transform_composed(self, tx_spec, target_spec_kind):
        if target_spec_kind in ['signed']:
            return SignedTxSpec(self.model, tx_spec, self.testnet)
        raise Exception('do not know how to transform tx spec')

    def transform_signed(self, tx_spec, target_spec_kind):
        raise Exception('do not know how to transform tx spec')

    def transform(self, tx_spec, target_spec_kind):
        spec_kind = self.classify_tx_spec(tx_spec)
        if spec_kind == None:
            raise Exception('spec kind is not recognized')
        if spec_kind == target_spec_kind:
            return tx_spec
        if spec_kind == 'basic':
            return self.transform_basic(tx_spec, target_spec_kind)
        elif spec_kind == 'operational':
            return self.transform_operational(tx_spec, target_spec_kind)
        elif spec_kind == 'composed':
            return self.transform_composed(tx_spec, target_spec_kind)
        elif spec_kind == 'signed':
            return self.transform_signed(tx_spec, target_spec_kind)
