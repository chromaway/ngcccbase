#!/usr/bin/env python

import unittest

from coloredcoinlib.colordef import (
    ones, POBColorDefinition, OBColorDefinition, BFTColorDefinition,
    ColorDefinition, GenesisColorDefinition, GENESIS_OUTPUT_MARKER,
    UNCOLORED_MARKER, InvalidColorError, InvalidTargetError)
from coloredcoinlib.colorvalue import SimpleColorValue
from coloredcoinlib.txspec import ComposedTxSpec, ColorTarget

from test_txspec import MockTX, MockOpTxSpec, i2seq


class TestColorDefinition(GenesisColorDefinition):
    CLASS_CODE = 'test'


class ColorDefinitionTester():
    def __init__(self, colordef):
        self.colordef = colordef
    def test(self, inputs, outputs, in_colorvalues, txhash="not genesis", inp_seq_indices=None):
        ins = []
        for i in in_colorvalues:
            if i is None:
                ins.append(None)
            else:
                ins.append(SimpleColorValue(colordef=self.colordef, value=i))
        tx = MockTX(txhash, inputs, outputs, inp_seq_indices)
        return [i and i.get_value() for i in self.colordef.run_kernel(tx, ins)]


class TestBaseDefinition(unittest.TestCase):

    def setUp(self):
        ColorDefinition.register_color_def_class(TestColorDefinition)
        self.txhash = 'color_desc_1'
        self.cd = TestColorDefinition(1, {'txhash': self.txhash,
                                          'outindex': 0, 'height':0})
        self.tx = MockTX(self.txhash, [], [])

    def test_markers(self):
        self.assertEqual(GENESIS_OUTPUT_MARKER.__repr__(), 'Genesis')
        self.assertEqual(UNCOLORED_MARKER.__repr__(), '')

    def test_from_color_desc(self):
        cd = ColorDefinition.from_color_desc(1, "test:%s:0:0" % self.txhash)
        self.assertTrue(isinstance(cd, TestColorDefinition))

    def test_get_color_def_cls_for_code(self):
        self.assertEqual(self.cd.get_color_def_cls_for_code('test'),
                         TestColorDefinition)

    def test_is_special_tx(self):
        self.assertTrue(self.cd.is_special_tx(self.tx))

    def test_repr(self):
        a = ColorDefinition(1)
        self.assertEqual(a.__repr__(), "Color Definition with 1")
        self.assertEqual(self.cd.__repr__(), "test:color_desc_1:0:0")


class TestOBC(unittest.TestCase):

    def setUp(self):
        self.obc = OBColorDefinition(1, {'txhash': 'genesis', 'outindex': 0})
        self.genesis_tx = MockTX('genesis', [], [])
        self.tester = ColorDefinitionTester(self.obc)

    def test_run_kernel(self):
        test = self.tester.test

        # genesis
        self.assertEqual(test([1], [1], [1], "genesis"), [1])
        self.assertEqual(test([4], [1, 3], [1], "genesis"), [1, 3])

        # simple transfer
        self.assertEqual(test([1], [1], [1]), [1])
        # canonical split
        self.assertEqual(test([2, 3], [5], [2, 3]), [5])
        # canonical combine
        self.assertEqual(test([5], [2, 3], [5]), [2, 3])
        # screwed up
        self.assertEqual(test([1, 2, 3, 1], [1, 7, 1], [None, 2, 3, None]), [None, None, None])

    def test_affecting_inputs(self):
        self.assertEqual(self.obc.get_affecting_inputs(self.genesis_tx, set()),
                         set())
        tx = MockTX('other', [1,2,4,5], [2,1,7,2])
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([0])),
                         set([tx.inputs[0], tx.inputs[1]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([0, 1])),
                         set([tx.inputs[0], tx.inputs[1]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([1])),
                         set([tx.inputs[1]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([1, 2])),
                         set([tx.inputs[1], tx.inputs[2], tx.inputs[3]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([2])),
                         set([tx.inputs[2], tx.inputs[3]]))
        self.assertEqual(self.obc.get_affecting_inputs(tx, set([3])),
                         set([tx.inputs[3]]))

    def test_compose_genesis_tx_spec(self):
        txspec = MockOpTxSpec([])
        cv = SimpleColorValue(colordef=UNCOLORED_MARKER, value=1)
        self.assertRaises(InvalidTargetError,
                          OBColorDefinition.compose_genesis_tx_spec, txspec)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertRaises(InvalidColorError,
                          OBColorDefinition.compose_genesis_tx_spec, txspec)
        cv = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER, value=1)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertTrue(isinstance(
                OBColorDefinition.compose_genesis_tx_spec(txspec),
                ComposedTxSpec))

    def test_compose_tx_spec(self):
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=1)
        cv2 = SimpleColorValue(colordef=self.obc, value=1)
        target1 = ColorTarget('addr1', cv1)
        target2 = ColorTarget('addr2', cv2)
        targets = [target1, target2]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.obc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        non = POBColorDefinition(2, {'txhash': 'something', 'outindex': 0})
        cv3 = SimpleColorValue(colordef=non, value=1)
        target3 = ColorTarget('addr3', cv3)
        targets = [cv3, cv2]
        txspec = MockOpTxSpec(targets)
        self.assertRaises(InvalidColorError, self.obc.compose_tx_spec, txspec)

    def test_from_color_desc(self):
        cd = OBColorDefinition.from_color_desc(1, "obc:doesnmatter:0:0")
        self.assertTrue(isinstance(cd, OBColorDefinition))
        self.assertRaises(InvalidColorError, OBColorDefinition.from_color_desc,
                          1, "blah:doesnmatter:0:0")
        

class TestPOBC(unittest.TestCase):

    def setUp(self):
        self.pobc = POBColorDefinition(1, {'txhash': 'genesis', 'outindex': 0})
        self.tester = ColorDefinitionTester(self.pobc)

    def test_run_kernel(self):
        # test the POBC color kernel
        test = self.tester.test

        # genesis
        self.assertEqual(test([10001], [10001], [1], "genesis"), [1])
        self.assertEqual(test([40001], [10001, 30000], [1], "genesis"), [1, None])
        self.assertEqual(test([10000, 1], [10001], [1], "genesis"), [1])
        self.pobc.genesis['outindex'] = 1
        self.assertEqual(test([40001], [30000, 10001], [1], "genesis"), [None, 1])
        self.pobc.genesis['outindex'] = 0
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

    def test_compose_genesis_tx_spec(self):
        cv = SimpleColorValue(colordef=self.pobc, value=5)
        txspec = MockOpTxSpec([])
        self.assertRaises(InvalidTargetError,
                          POBColorDefinition.compose_genesis_tx_spec, txspec)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertRaises(InvalidColorError,
                          POBColorDefinition.compose_genesis_tx_spec, txspec)

        cv = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER, value=5)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertTrue(isinstance(
                POBColorDefinition.compose_genesis_tx_spec(txspec),
                ComposedTxSpec))

    def test_compose_tx_spec(self):
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
        cv2 = SimpleColorValue(colordef=self.pobc, value=10000)
        targets = [ColorTarget('addr1', cv1), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.pobc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=20000)
        cv2 = SimpleColorValue(colordef=self.pobc, value=20000)
        targets = [ColorTarget('addr1', cv1), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.pobc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        non = OBColorDefinition(2, {'txhash': 'something', 'outindex': 0})
        cv3 = SimpleColorValue(colordef=non, value=2)
        targets = [ColorTarget('addr1', cv3), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertRaises(InvalidColorError, self.pobc.compose_tx_spec, txspec)

    def test_from_color_desc(self):
        cd = POBColorDefinition.from_color_desc(1, "pobc:doesnmatter:0:0")
        self.assertTrue(isinstance(cd, POBColorDefinition))
        self.assertRaises(InvalidColorError,
                          POBColorDefinition.from_color_desc, 1,
                          "blah:doesnmatter:0:0")


class TestBFTC(unittest.TestCase):
    def setUp(self):
        self.bftc = BFTColorDefinition(2, {'txhash': 'genesis', 'outindex': 0})
        self.tester = ColorDefinitionTester(self.bftc)

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

    def test_run_kernel(self):
        # test the BFTC color kernel
        test = self.tester.test

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



if __name__ == '__main__':
    unittest.main()
