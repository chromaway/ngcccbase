#!/usr/bin/env python

import unittest

from coloredcoinlib import (ColorSet, OBColorDefinition, POBColorDefinition,
                            SimpleColorValue)

from ngcccbase.p2ptrade.protocol_objects import (
    EOffer, MyEOffer, ETxSpec, EProposal, MyEProposal,
    MyReplyEProposal, ForeignEProposal)


class TestEOffer(unittest.TestCase):

    def setUp(self):
        self.colordef0 = POBColorDefinition(
            1, {'txhash': 'genesis', 'outindex': 0})
        self.colordef1 = OBColorDefinition(
            2, {'txhash': 'genesis', 'outindex': 0})
        self.colorvalue0 = SimpleColorValue(colordef=self.colordef0,
                                    value=1, label='test')
        self.colorvalue1 = SimpleColorValue(colordef=self.colordef0,
                                    value=2, label='test2')
        self.colorvalue2 = SimpleColorValue(colordef=self.colordef1,
                                    value=1)

        self.e0 = MyEOffer.from_data({'oid':1,
                                      'A': self.colorvalue0,
                                      'B': self.colorvalue1 })
        self.e1 = MyEOffer.from_data({'oid':2,
                                      'A': self.colorvalue0,
                                      'B': self.colorvalue1 })

    def test_expired(self):
        self.e0.refresh(100000)
        self.assertFalse(self.e0.expired())

    def test_get_data(self):
        self.assertEqual(self.e0.get_data()['A'], self.e1.get_data()['A'])

    def test_matches(self):
        self.assertFalse(self.e0.matches(self.e1))
        self.e1.A = self.colorvalue1
        self.e1.B = self.colorvalue0
        self.assertTrue(self.e0.matches(self.e1))

    def test_is_same(self):
        self.assertTrue(self.e0.is_same_as_mine(self.e1))
        self.e0.A = self.colorvalue2
        self.assertFalse(self.e0.is_same_as_mine(self.e1))


if __name__ == '__main__':
    unittest.main()
