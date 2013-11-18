""" Transaction specification language """


class OperationalTxSpec(object):
    """transaction specification which is ready to be operated on
       (has all the necessary data)"""
    def get_targets(self):
        """returns a list of targets: tuples
           (target_addr, color_def, colorvalue)"""
        raise Exception('not implemented')

    def select_coins(self, color_id, colorvalue):
        """returns a list of UTXO objects with color_id
           which have at least the colorvalue"""
        raise Exception('not implemented')

    def get_change_addr(self, color_id):
        """returns an address which can be used as
           a change for this color_id"""
        raise Exception('not implemented')

    def get_required_fee(self, tx_size):
        """returns fee for a certain tx size"""
        raise Exception('not implemented')

    def is_monocolor(self):
        targets = self.get_targets()
        color_def = targets[0][1]
        for target in targets:
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
