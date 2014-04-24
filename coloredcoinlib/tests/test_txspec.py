#!/usr/bin/env python

import unittest

from coloredcoinlib.colorvalue import SimpleColorValue
from coloredcoinlib.colordef import (UNCOLORED_MARKER, OBColorDefinition,
                                     EPOBCColorDefinition)
from coloredcoinlib.txspec import (ColorTarget, OperationalTxSpec,
                                   ComposedTxSpec)


class MicroMock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.prevout = MockTXIn('2', 1)


class MockTXIn(object):
    def __init__(self, h, n):
        self.hash = h
        self.n = n
    def is_null(self):
        return False

class MockTXElement:
    def __init__(self, value, inp_seq_indices=None):
        self.value = value
        self.prevout = MockTXIn('2', 1)
        if inp_seq_indices is None:
            inp_seq_indices = [0,1,4,5,6,7]
        self.prevtx = MockTX('tmp', [], [], inp_seq_indices)
    def __repr__(self):
        return "<MockTXElement: %s>" % self.value


def i2seq(i):
    if i is None:
        return 0
    return 2**(i)


class MockRawTX:
    def __init__(self, inp_seq_indices):
        nSequence = 0
        for i in inp_seq_indices:
            nSequence += i2seq(i)
        self.vin = [MicroMock(nSequence=nSequence)]


class MockTX:
    def __init__(self, h, inputs, outputs, inp_seq_indices=None, prev_seq_indices=None):
        self.hash = h
        self.inputs = [MockTXElement(satoshis, prev_seq_indices) for satoshis in inputs]
        self.outputs = [MockTXElement(satoshis) for satoshis in outputs]
        self.raw = MockRawTX(inp_seq_indices or [None for _ in inputs])
    def ensure_input_values(self):
        pass


class MockUTXO(ComposedTxSpec.TxIn):
    def __init__(self, colorvalues):
        self.colorvalues = colorvalues
        self.value = sum([cv.get_value() for cv in colorvalues])
    def set_nSequence(self, nSequence):
        self.nSequence = nSequence


class MockOpTxSpec(OperationalTxSpec):
    def __init__(self, targets):
        self.targets = targets
    def get_targets(self):
        return self.targets
    def get_required_fee(self, amount):
        return SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
    def get_change_addr(self, addr):
        return 'changeaddr'
    def get_dust_threshold(self):
        return SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
    def select_coins(self, colorvalue, use_fee_estimator=None):
        cvs = [
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=10000),
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=20000),
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=10000),
            SimpleColorValue(colordef=colorvalue.get_colordef(), value=10000)
            ]
        s = SimpleColorValue.sum(cvs)
        return [MockUTXO([cv]) for cv in cvs], s


class TestTxSpec(unittest.TestCase):
    def setUp(self):
        self.colordef1 = EPOBCColorDefinition(
            1, {'txhash': 'genesis', 'outindex': 0})
        self.colordef2 = OBColorDefinition(
            2, {'txhash': 'genesis', 'outindex': 0})
        self.cv1 = SimpleColorValue(colordef=self.colordef1,
                                    value=1, label='test')
        self.cv2 = SimpleColorValue(colordef=self.colordef1,
                                    value=2, label='test2')
        self.cv3 = SimpleColorValue(colordef=self.colordef2,
                                    value=1)
        self.ct1 = ColorTarget('address1', self.cv1)
        self.ct2 = ColorTarget('address2', self.cv2)
        self.ct3 = ColorTarget('address3', self.cv3)
        self.txspec = MockOpTxSpec([self.ct1, self.ct2])

    def test_repr(self):
        self.assertEqual(self.ct1.__repr__(), 'address1: test: 1')

    def test_get_colordef(self):
        self.assertEqual(self.ct1.get_colordef(), self.colordef1)

    def test_get_value(self):
        self.assertEqual(self.ct1.get_value(), self.cv1.get_value())

    def test_sum(self):
        cts = [self.ct1, self.ct2, ColorTarget('address3',self.cv2)]
        self.assertEqual(ColorTarget.sum(cts).get_value(), 5)
        self.assertEqual(ColorTarget.sum([]), 0)

    def test_opspec(self):
        self.assertTrue(self.txspec.is_monocolor())
        spec = MockOpTxSpec([self.ct1, self.ct2, self.ct3])
        self.assertFalse(spec.is_monocolor())

    def test_cspec(self):
        txo1 = ComposedTxSpec.TxOut(1, 'addr')
        txo2 = ComposedTxSpec.TxOut(2, 'addr2')
        outs = [txo1, txo2]
        c = ComposedTxSpec(None)
        c.add_txins([])
        c.add_txouts([txo1, txo2])
        self.assertEqual(c.get_txins(), [])
        self.assertEqual(c.get_txouts(), outs)


if __name__ == '__main__':
    unittest.main()
