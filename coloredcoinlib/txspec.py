""" Transaction specification language """
from blockchain import script_to_raw_address


class OperationalTxSpec(object):
    """transaction specification which is ready to be operated on
       (has all the necessary data)"""
    def get_targets(self):
        """returns a list of targets: tuples
           (target_addr, color_def, colorvalue)"""
        raise Exception('not implemented')

    def select_coins(self, color_def, colorvalue):
        """returns a list of UTXO objects with color defined in color_def
           whose colorvalue sums have at least the colorvalue"""
        raise Exception('not implemented')

    def get_change_addr(self, color_def):
        """returns an address which can be used as
           a change for this color_def"""
        raise Exception('not implemented')

    def get_required_fee(self, tx_size):
        """returns fee for a certain tx size"""
        raise Exception('not implemented')

    def is_monocolor(self):
        targets = self.get_targets()
        color_def = targets[0][1]
        for target in targets[1:]:
            if target[1] is not color_def:
                return False
        return True


class ComposedTxSpec(object):
    """specification of a transaction which is already composed,
       but isn't signed yet"""

    class TxIn(object):
        __slots__ = ['utxo']

        def __init__(self, utxo):
            self.utxo = utxo

    class TxOut(object):
        __slots__ = ['value', 'target_addr']

        def __init__(self, value, target_addr):
            self.value = value
            self.target_addr = target_addr

    def __init__(self, txins, txouts):
        self.txins = txins
        self.txouts = txouts

    def get_txins(self):
        return self.txins

    def get_txouts(self):
        return self.txouts

    @classmethod
    def from_pycoin_tx(cls, ccc, pycoin_tx):
        txins, txouts = [], []

        for py_txin in pycoin_tx.txs_in:
            # lookup the previous hash and generate the utxo
            in_txhash, in_outindex = py_txin.previous_hash, py_txin.previous_index
            in_tx = ccc.blockchain_state.get_tx(in_txhash)
            value = in_tx.outputs[in_outindex].value
            raw_address = script_to_raw_address(py_txin.script)
            address = ccc.raw_to_address(raw_address)

            utxo = {
                'txhash': in_txhash,
                'outindex': in_outindex,
                'address': address,
                'value': value,
                'script': py_txin.script.encode('hex'),
                'scantime': -1,
                'commitment': -1,
                }
            txins.append(TxIn(utxo))
        for py_txout in pycoin_tx.txs_out:
            script = py_txout.script
            raw_address = script_to_raw_address(script)
            address = ccc.raw_to_address(raw_address)
            txouts.append(TxOut(py_txout.coin_value, address))
        return cls(txins, txouts)
