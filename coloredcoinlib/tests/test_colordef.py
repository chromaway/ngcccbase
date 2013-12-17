#!/usr/bin/env python

import unittest

from coloredcoinlib.colordef import ones, POBColorDefinition, BFTColorDefinition


class MicroMock(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class MockTXElement:
    def __init__(self, value):
        self.value = value

def i2seq(i):
    if i is None:
        return 0
    return 2**(i)

class MockRawTX:
    def __init__(self, inp_seq_indices):
        self.vin = [MicroMock(nSequence=i2seq(i)) for i in inp_seq_indices]

class MockTX:
    def __init__(self, h, inputs, outputs, inp_seq_indices=None):
        self.hash = h
        self.inputs = [MockTXElement(satoshis) for satoshis in inputs]
        self.outputs = [MockTXElement(satoshis) for satoshis in outputs]
        self.raw = MockRawTX(inp_seq_indices or [None for _ in inputs])
    def ensure_input_values(self):
        pass
class ColorDefinitionTester():
    def __init__(self, colordef):
        self.colordef = colordef
    def test(self, inputs, outputs, in_colorvalues, txhash="not genesis", inp_seq_indices=None):
        tx = MockTX(txhash, inputs, outputs, inp_seq_indices)
        return [i and i[0] for i in self.colordef.run_kernel(tx, in_colorvalues)]


class TestColordef(unittest.TestCase):
    def test_pocb_color_kernel(self):
        # test the POBC color kernel
        pobc = POBColorDefinition(
            "testcolor", {'txhash': 'genesis', 'outindex': 0})
        t = ColorDefinitionTester(pobc)
        test = t.test

        # genesis
        self.assertEqual(test([10001], [10001], [1], "genesis"), [1])
        self.assertEqual(test([40001], [10001, 30000], [1], "genesis"), [1, None])
        self.assertEqual(test([10000, 1], [10001], [1], "genesis"), [1])
        pobc.genesis['outindex'] = 1
        self.assertEqual(test([40001], [30000, 10001], [1], "genesis"), [None, 1])
        pobc.genesis['outindex'] = 0
        # simple transfer
        self.assertEqual(test([10001], [10001], [1]), [1])
        # canonical split
        self.assertEqual(test([10002, 10003], [10005], [2, 3]), [5])
        # canonical combine
        self.assertEqual(test([10005], [10002, 10003], [5]), [2, 3])
        # null values before and after
        self.assertEqual(test([10001, 10002, 10003, 50000], [10001, 10005, 50000], [None, 2, 3, None]), [None, 5, None])
        # ignore below-padding values
        self.assertEqual(test([10001, 10002, 10003, 50000, 100, 20000], [10001, 10005, 100, 70000, 100], [None, 2, 3, None]), [None, 5])
        # color values don't add up the same
        self.assertEqual(test([10001, 10002, 10003, 10001, 50000], [10001, 10005, 50001], [None, 2, 3, 1, None]), [None, None, None])
        # value before is not the same
        self.assertEqual(test([10001, 10002, 10003, 50000], [10002, 10005, 49999], [None, 2, 3, None]), [None, None, None])
        # nonnull color values are not adjacent
        self.assertEqual(test([10001, 10002, 10003, 10004, 50000], [10001, 10006, 49999], [None, 2, None, 4, None]), [None, None, None])
        # sequence before don't add up the same
        self.assertEqual(test([10005, 10001, 10002, 10003, 50000], [10004, 10001, 10005, 40000], [None, None, 2, 3, None]), [None, None, None, None])
        # sequence before does add up the same
        self.assertEqual(test([10005, 10001, 10002, 10003, 50001], [10005, 10001, 10005, 40000], [None, None, 2, 3, None]), [None, None, 5, None])
        # split to many
        self.assertEqual(test([10005, 10001, 10005, 50001], [10005, 10001, 10001, 10001, 10001, 10001, 10001, 40000], [None, None, 5, None]), [None, None, 1, 1, 1, 1, 1, None])
        # combine many
        self.assertEqual(test([10005, 10001, 10001, 10001, 10001, 10001, 10001, 40000], [10005, 10001, 10005, 50001], [None, None, 1, 1, 1, 1, 1, None]), [None, None, 5, None])
        # split and combine
        self.assertEqual(test([10001, 10002, 10003, 10004, 10005, 10006, 50000], [10001, 10005, 10009, 10006, 50000], [None, 2, 3, 4, 5, 6, None]), [None, 5, 9, 6, None])
        # combine and split
        self.assertEqual(test([10005, 10009, 10006, 50000], [10002, 10003, 10004, 10005, 10006, 50000], [5, 9, 6, None]), [2, 3, 4, 5, 6, None])

    def test_ones(self):
        self.assertEqual(list(ones(0)), [])
        self.assertEqual(list(ones(1)), [0])
        self.assertEqual(list(ones(10)), [1, 3])
        self.assertEqual(list(ones(42)), [1, 3, 5])
        self.assertEqual(list(ones(127)), [0, 1, 2, 3, 4, 5, 6])
        self.assertEqual(list(ones(987654321)), [0, 4, 5, 7, 11, \
                 13, 14, 17, 18, 19, 20, 22, 23, 25, 27, 28, 29])

    def test_i2seq(self):
        self.assertEqual(i2seq(None), 0)
        self.assertEqual(i2seq(0), 1)
        self.assertEqual(i2seq(1), 2)
        self.assertEqual(i2seq(2), 4)
        self.assertEqual(i2seq(3), 8)
        self.assertEqual(i2seq(4), 16)
        self.assertEqual(i2seq(10), 2**10)

    def test_bftc_color_kernel(self):
        # test the BFTC color kernel
        bftc = BFTColorDefinition(
            "testcolor", {'txhash': 'genesis', 'outindex': 0})
        t = ColorDefinitionTester(bftc)
        test = t.test

        # genesis
        self.assertEqual(test([1000], [1000], [None], "genesis"), [1000])
        # non genesis, no bitfield tag, no input color
        self.assertEqual(test([1000], [1000], [None]), [None])
        # non genesis, no bitfield tag, input colorvalue
        self.assertEqual(test([1000], [1000], [1000]), [None])
        # non genesis, bitfield tag, no input colorvalue
        self.assertEqual(test([1000], [1000], [None], inp_seq_indices=[0]), [None])
        # non genesis, bitfield tag, input colorvalue
        self.assertEqual(test([1000], [1000], [4000], inp_seq_indices=[0]), [4000])
        
        # wrong index in nSequence
        self.assertEqual(test([1000], [1000], [10], inp_seq_indices=[7]), [None])