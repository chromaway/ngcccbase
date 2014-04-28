""" Transaction specification language """

from blockchain import CTxIn
from colorvalue import ColorValue


class InvalidColorIdError(Exception):
    pass


class ZeroSelectError(Exception):
    pass


class ColorTarget(object):
    def __init__(self, address, colorvalue):
        self.address = address
        self.colorvalue = colorvalue

    def get_colordef(self):
        return self.colorvalue.get_colordef()

    def get_color_id(self):
        return self.colorvalue.get_color_id()

    def is_uncolored(self):
        return self.colorvalue.is_uncolored()

    def get_address(self):
        return self.address

    def get_value(self):
        return self.colorvalue.get_value()

    def get_satoshi(self):
        return self.colorvalue.get_satoshi()

    def __repr__(self):
        return "%s: %s" % (self.get_address(), self.colorvalue)

    @classmethod
    def sum(cls, targets):
        if len(targets) == 0:
            return 0
        c = targets[0].colorvalue.__class__
        return c.sum([t.colorvalue for t in targets])


class OperationalTxSpec(object):
    """transaction specification which is ready to be operated on
       (has all the necessary data)"""
    def get_targets(self):
        """returns a list of ColorTargets"""
        raise Exception('not implemented')  # pragma: no cover

    def select_coins(self, colorvalue, use_fee_estimator=None):
        """returns a list of UTXO objects with whose colordef is
        the same as <colorvalue> and have a sum colorvalues
        have at least the <colorvalue>.
        For uncolored coins sum of values of UTXO objects must
        also include a fee (if <use_fee_estimator> parameter is 
        provided, usually it is composed_tx_spec)."""
        raise Exception('not implemented')  # pragma: no cover

    def get_change_addr(self, color_def):
        """returns an address which can be used as
           a change for this color_def"""
        raise Exception('not implemented')  # pragma: no cover

    def get_required_fee(self, tx_size):
        """returns ColorValue object representing the fee for
        a certain tx size"""
        raise Exception('not implemented')  # pragma: no cover

    def get_dust_threshold(self):
        """returns ColorValue object representing smallest 
        satoshi value which isn't dust according to current
        parameters"""
        raise Exception('not implemented')  # pragma: no cover

    def is_monocolor(self):
        targets = self.get_targets()
        color_def = targets[0].get_colordef()
        for target in targets[1:]:
            if target.get_colordef() is not color_def:
                return False
        return True

    def make_composed_tx_spec(self):
        return ComposedTxSpec(self)


class ComposedTxSpec(object):
    """specification of a transaction which is already composed,
       but isn't signed yet"""

    class TxIn(CTxIn):
        pass

    class TxOut(object):
        __slots__ = ['value', 'target_addr']

        def __init__(self, value, target_addr):
            self.value = value
            self.target_addr = target_addr

    class FeeChangeTxOut(TxOut):
        pass

    def __init__(self, operational_tx_spec=None):
        self.txins = []
        self.txouts = []
        self.operational_tx_spec = operational_tx_spec

    def add_txin(self, txin):
        assert isinstance(txin, self.TxIn)
        self.txins.append(txin)

    def add_txout(self, txout=None, value=None, target_addr=None, 
                  target=None, is_fee_change=False):
        if not txout:
            if not value:
                if target and target.is_uncolored():
                    value = target.get_value()
                else:
                    raise Exception("error in ComposedTxSpec.add_txout: no\
value is provided and target is not uncolored")
            if isinstance(value, ColorValue):
                if value.is_uncolored():
                    value = value.get_value()
                else:
                    raise Exception("error in ComposedTxSpec.add_txout: no\
value isn't uncolored")
            if not target_addr:
                target_addr = target.get_address()      
            cls = self.FeeChangeTxOut if is_fee_change else self.TxOut
            txout = cls(value, target_addr)
        self.txouts.append(txout)

    def add_txouts(self, txouts):
        for txout in txouts:
            if isinstance(txout, ColorTarget):
                self.add_txout(target=txout)
            elif isinstance(txout, self.TxOut):
                self.add_txout(txout=txout)
            else:
                raise Exception('wrong txout instance')

    def add_txins(self, txins):
        for txin in txins:
            self.add_txin(txin)

    def get_txins(self):
        return self.txins

    def get_txouts(self):
        return self.txouts

    def estimate_size(self, extra_txins=0, extra_txouts=0, extra_bytes=0):
        return (181 * (len(self.txins) + extra_txins) + 
                34 * (len(self.txouts) + extra_txouts) + 
                10 + extra_bytes)

    def estimate_required_fee(self, extra_txins=0, extra_txouts=1, extra_bytes=0):
        return self.operational_tx_spec.get_required_fee(
            self.estimate_size(extra_txins=extra_txins,
                               extra_txouts=extra_txouts,
                               extra_bytes=extra_bytes))

    def get_fee(self):
        sum_txins = sum([inp.value 
                         for inp in self.txins])
        sum_txouts = sum([out.value
                          for out in self.txouts])
        return sum_txins - sum_txouts
