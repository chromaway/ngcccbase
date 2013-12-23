""" Transaction specification language """

from blockchain import CTxIn


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

    def select_coins(self, colorvalue):
        """returns a list of UTXO objects with whose colordef is
        the same as <colorvalue> and have a sum colorvalues
        have at least the <colorvalue>"""
        raise Exception('not implemented')  # pragma: no cover

    def get_change_addr(self, color_def):
        """returns an address which can be used as
           a change for this color_def"""
        raise Exception('not implemented')  # pragma: no cover

    def get_required_fee(self, tx_size):
        """returns ColorValue object representing the fee for
        a certain tx size"""
        raise Exception('not implemented')  # pragma: no cover

    def is_monocolor(self):
        targets = self.get_targets()
        color_def = targets[0].get_colordef()
        for target in targets[1:]:
            if target.get_colordef() is not color_def:
                return False
        return True


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

    def __init__(self, txins, txouts):
        self.txins = txins
        self.txouts = txouts

    def get_txins(self):
        return self.txins

    def get_txouts(self):
        return self.txouts

