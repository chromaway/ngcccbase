#!/usr/bin/env python

import random
import unittest

from coloredcoinlib.colordef import (
    EPOBCColorDefinition, OBColorDefinition,
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
        non = EPOBCColorDefinition(2, {'txhash': 'something', 'outindex': 0})
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
        

class TestEPOBC(unittest.TestCase):

    def setUp(self):
        self.epobc = EPOBCColorDefinition(1, {'txhash': 'genesis',
                                              'outindex': 0, 'height': 0})
        self.tester = ColorDefinitionTester(self.epobc)
        self.tag_class = EPOBCColorDefinition.Tag

    def test_tag_closest_padding_code(self):
        self.assertEqual(self.tag_class.closest_padding_code(0), 0)
        for i in range(15):
            if i > 0:
                self.assertEqual(self.tag_class.closest_padding_code(2**i), i)
            self.assertEqual(self.tag_class.closest_padding_code(2**i+1), i+1)
        self.assertRaises(Exception,
                          self.tag_class.closest_padding_code, 2**63+1)

    def test_tag_from_nsequence(self):
        self.assertEqual(self.tag_class.from_nSequence(1), None)
        # xfer is 110011 in binary = 51
        xfer_tag = self.tag_class.from_nSequence(512 + 51)
        self.assertEqual(xfer_tag.is_genesis, False)
        self.assertEqual(xfer_tag.padding_code, 8)
        # genesis is 100101 in binary = 37
        genesis_tag = self.tag_class.from_nSequence(2048 + 37)
        self.assertEqual(genesis_tag.is_genesis, True)
        self.assertEqual(genesis_tag.padding_code, 32)

    def test_tag_to_nsequence(self):
        n = random.randint(0,63) * 64 + 51
        xfer_tag = self.tag_class.from_nSequence(n)
        self.assertEqual(xfer_tag.to_nSequence(), n)

    def test_get_tag(self):
        tx = MockTX("random", [1,1,1], [2,1], [0,1,4,5,9])
        self.assertEqual(EPOBCColorDefinition.get_tag(tx).padding_code, 8)
        def tmp():
            return True
        tx.raw.vin[0].prevout.is_null = tmp
        self.assertEqual(EPOBCColorDefinition.get_tag(tx), None)

    def test_run_kernel(self):
        # test the EPOBC color kernel
        test = self.tester.test

        # genesis
        # pad 8, direct
        self.assertEqual(test([9], [9], [1], "genesis", [0,2,5,6,7]), [1])
        # pad 32, split
        self.assertEqual(test([59], [33, 26], [1], "genesis", [0,2,5,6,8]), [1, None])
        # pad 16, join
        self.assertEqual(test([12, 5], [17], [1], "genesis", [0,2,5,8]), [1])

        # different outindex
#        self.epobc.genesis['outindex'] = 1
#        self.assertEqual(test([30], [27, 3], [1], "genesis", [0,2,5,6]), [None, 1])
#        self.epobc.genesis['outindex'] = 0

        # transfer
        xfer_8 = [0, 1, 4, 5, 6, 7]
        # pad 8, direct
        self.assertEqual(test([9], [9], [1], "xfer", xfer_8), [1])
        # pad 8, join
        self.assertEqual(test([10, 11], [13], [2, 3], "xfer", xfer_8), [5])
        # pad 8, split
        self.assertEqual(test([13], [10, 11], [5], "xfer", xfer_8), [2, 3])

        # 0's all around
        self.assertEqual(test([8, 8, 8], [8, 8, 8], [None, None, None], "xfer", xfer_8), [None, None, None])

        # null values before and after
        self.assertEqual(test([9, 10, 11, 20], [9, 13, 20], [None, 2, 3, None], "xfer", xfer_8), [None, 5, None])

        # ignore below-padding values -- DOES NOT PASS
#        self.assertEqual(test([5, 10, 11, 5], [5, 13, 5], [2, 3, None], "xfer", xfer_8), [None, 5, None])
        # color values don't add up the same
        self.assertEqual(test([9, 10, 11], [13, 15, 0], [1, 2, 3], "xfer", xfer_8), [5, None, None])
        self.assertEqual(test([9, 10, 11], [9, 15, 0], [1, 2, 3], "xfer", xfer_8), [1, None, None])
        self.assertEqual(test([9, 10, 11], [19, 9, 0], [1, 2, 3], "xfer", xfer_8), [None, None, None])

        # sum before color values is not the same
        self.assertEqual(test([5, 10, 11], [6, 13], [None, 2, 3], "xfer", xfer_8), [None, None])
        # nonnull color values are not adjacent
        self.assertEqual(test([10, 10, 10, 12, 10], [10, 32, 10], [None, 2, None, 4, None], "xfer", xfer_8), [None, None, None])
        # sequence before don't add up the same
        self.assertEqual(test([10, 10, 10, 11, 10], [15, 13, 10], [None, None, 2, 3, None], "xfer", xfer_8), [None, None, None])
        # sequence before does add up the same
        self.assertEqual(test([10, 10, 10, 11, 10], [9, 11, 13, 10], [None, None, 2, 3, None], "xfer", xfer_8), [None, None, 5, None])
        # split to many
        self.assertEqual(test([10, 10, 13, 40], [10, 10, 9, 9, 9, 9, 9, 5], [None, None, 5, None], "xfer", xfer_8), [None, None, 1, 1, 1, 1, 1, None])
        # combine many
        self.assertEqual(test([10, 9, 9, 9, 9, 9, 10], [10, 13, 32], [None, 1, 1, 1, 1, 1, None], "xfer", xfer_8), [None, 5, None])
        # split and combine
        self.assertEqual(test([10, 10, 11, 12, 13, 14, 10], [10, 13, 17, 14, 30], [None, 2, 3, 4, 5, 6, None], "xfer", xfer_8), [None, 5, 9, 6, None])
        # combine and split
        self.assertEqual(test([13, 17, 14, 30], [10, 11, 12, 13, 14, 10], [5, 9, 6, None], "xfer", xfer_8), [2, 3, 4, 5, 6, None])

    def test_compose_genesis_tx_spec(self):
        cv = SimpleColorValue(colordef=self.epobc, value=5)
        txspec = MockOpTxSpec([])
        self.assertRaises(InvalidTargetError,
                          EPOBCColorDefinition.compose_genesis_tx_spec, txspec)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertRaises(InvalidColorError,
                          EPOBCColorDefinition.compose_genesis_tx_spec, txspec)

        cv = SimpleColorValue(colordef=GENESIS_OUTPUT_MARKER, value=5)
        target = ColorTarget('addr', cv)
        txspec = MockOpTxSpec([target])
        self.assertTrue(isinstance(
                EPOBCColorDefinition.compose_genesis_tx_spec(txspec),
                ComposedTxSpec))

    def test_compose_tx_spec(self):
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000)
        cv2 = SimpleColorValue(colordef=self.epobc, value=10000)
        targets = [ColorTarget('addr1', cv1), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.epobc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        cv1 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=20000)
        cv2 = SimpleColorValue(colordef=self.epobc, value=20000)
        targets = [ColorTarget('addr1', cv1), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertTrue(isinstance(self.epobc.compose_tx_spec(txspec),
                                   ComposedTxSpec))
        non = OBColorDefinition(2, {'txhash': 'something', 'outindex': 0})
        cv3 = SimpleColorValue(colordef=non, value=2)
        targets = [ColorTarget('addr1', cv3), ColorTarget('addr1', cv2)]
        txspec = MockOpTxSpec(targets)
        self.assertRaises(InvalidColorError, self.epobc.compose_tx_spec, txspec)

    def test_from_color_desc(self):
        cd = EPOBCColorDefinition.from_color_desc(1, "epobc:doesnmatter:0:0")
        self.assertTrue(isinstance(cd, EPOBCColorDefinition))
        self.assertRaises(InvalidColorError,
                          EPOBCColorDefinition.from_color_desc, 1,
                          "blah:doesnmatter:0:0")



if __name__ == '__main__':
    unittest.main()
