#!/usr/bin/env python

import unittest
from ngcccbase.p2ptrade.protocol_objects import (
    EOffer, MyEOffer, ETxSpec, EProposal, MyEProposal
)


class MockEWalletController(object):

  def __init__(self):
    self.model = "model"
    self.published = []

  def make_etx_spec(self, inputs, targets):
    return ETxSpec(inputs, targets, None)

  def publish_tx(rtxs, offer):
    self.published.append([rtxs, offer])

  def make_reply_tx(etx_spec, A, B):
    return "tx"


class TestEOffer(unittest.TestCase):

  def test_random_default_id(self):
    a = EOffer(0, None, None)
    b = EOffer(1, None, None)
    self.assertNotEqual(a.oid, 0)
    self.assertEqual(b.oid, 1)

  def test_unrefreshed_expired(self):
    eo = EOffer(0, None, None)
    self.assertTrue(eo.expired())

  def test_expired(self):
    eo = EOffer(0, None, None)
    eo.refresh(-1)
    self.assertTrue(eo.expired())

  def test_unexpired(self):
    eo = EOffer(0, None, None)
    eo.refresh(42)
    self.assertFalse(eo.expired())

  def test_unexpired_shift(self):
    eo = EOffer(0, None, None)
    eo.refresh(0)
    self.assertTrue(eo.expired_shift(42))
    self.assertFalse(eo.expired_shift(-42))

  def test_convert_from_data(self):
    data = {'oid': 1, 'A':"A", 'B':"B"}
    result = EOffer.from_data(data)
    expected = EOffer(1, "A", "B")
    self.assertEqual(result, expected)

  def test_convert_to_data(self):
    src = EOffer(1, "A", "B")
    result = src.get_data()
    expected = {'oid': 1, 'A':"A", 'B':"B"}
    self.assertEqual(result, expected)

  def test_is_same_ignores_id(self):
    eo = EOffer(1, "A", "B")
    self.assertTrue(eo.is_same_as_mine(EOffer(2, "A", "B")))

  def test_is_same_ignores_expired(self):
    eo = EOffer(1, "A", "B")
    x = EOffer(1, "A", "B")
    x.refresh(42)
    self.assertTrue(eo.is_same_as_mine(x))

  def test_is_same_equality_table(self):
    eo = EOffer(1, "A", "B")
    self.assertTrue(eo.is_same_as_mine(EOffer(1, "A", "B")))
    self.assertFalse(eo.is_same_as_mine(EOffer(1, "X", "B")))
    self.assertFalse(eo.is_same_as_mine(EOffer(1, "A", "X")))
    self.assertFalse(eo.is_same_as_mine(EOffer(1, "X", "X")))

  def test_matches_ignores_id(self):
    eo = EOffer(1, "A", "B")
    self.assertTrue(eo.matches(EOffer(2, "B", "A")))

  def test_matches_ignores_expired(self):
    eo = EOffer(1, "A", "B")
    x = EOffer(1, "B", "A")
    x.refresh(42)
    self.assertTrue(eo.matches(x))

  def test_matches_equality_table(self):
    eo = EOffer(1, "A", "B")
    self.assertTrue(eo.matches(EOffer(1, "B", "A")))
    self.assertFalse(eo.matches(EOffer(1, "B", "X")))
    self.assertFalse(eo.matches(EOffer(1, "X", "A")))
    self.assertFalse(eo.matches(EOffer(1, "X", "X")))


class TestMyEOffer(unittest.TestCase):

  def test_auto_post_default(self):
    meo = MyEOffer(1, "A", "B")
    self.assertTrue(meo.auto_post)

  def test_compatibility(self):
    meo = MyEOffer(1, "A", "B")
    eo = EOffer(1, "A", "B")
    self.assertTrue(meo.is_same_as_mine(eo))

  def test_convert_from_data(self):
    data = {'oid': 1, 'A':"A", 'B':"B"}
    result = MyEOffer.from_data(data)
    expected = MyEOffer(1, "A", "B")
    self.assertEqual(result, expected)


class TestETxSpec(unittest.TestCase):

  def test_convert_from_data(self):
    data = {'inputs':"i", 'targets':"t"}
    result = ETxSpec.from_data(data)
    expected = ETxSpec("i", "t", None)
    self.assertEqual(result, expected)

  def test_convert_to_data(self):
    src = ETxSpec("i", "t", None)
    result = src.get_data()
    expected = {'inputs':"i", 'targets':"t"}
    self.assertEqual(result, expected)


class TestEProposal(unittest.TestCase):

  def test_convert_to_data(self):
    eo = EOffer(1, "A", "B")
    src = EProposal("pid", "ewctrl", eo)
    result = src.get_data()
    expected = {'pid':"pid", 'offer':eo.get_data()}
    self.assertEqual(result, expected)


class TestMyEProposal(unittest.TestCase):

  def test_construction(self):
    ewctrl = MockEWalletController()
    a = EOffer(1, "A", "B")
    b = EOffer(1, "B", "A")
    mep = MyEProposal(ewctrl, a, b)
    self.assertEqual(mep.my_offer, b)

  def test_unmatching_offers(self):
    ewctrl = MockEWalletController()
    a = EOffer(1, "A", "B")
    b = EOffer(2, "X", "Y")
    self.assertRaises(Exception, MyEProposal, ewctrl, a, b)

  def test_get_data_etx_spec(self):
    ewctrl = MockEWalletController()
    a = EOffer(1, "A", "B")
    b = EOffer(1, "B", "A")
    src = MyEProposal(ewctrl, a, b)
    result = src.get_data()
    expected = {
        'pid':src.pid, 'offer':a.get_data(), 
        'etx_spec': {'inputs':"B", 'targets':"A"}
    }
    self.assertEqual(result, expected)
    self.assertEqual(result.get('etx_data'), None)

  def test_get_data_etx_data(self):
    ewctrl = MockEWalletController()
    a = EOffer(1, "A", "B")
    b = EOffer(1, "B", "A")
    src = MyEProposal(ewctrl, a, b)
    src.etx_data = "etx_data"
    result = src.get_data()
    expected = {'pid':src.pid, 'offer':a.get_data(), 'etx_data': "etx_data"}
    self.assertEqual(result, expected)
    self.assertEqual(result.get('etx_spec'), None)

  def test_process_reply(self):
    pass # tested by ngcccbase.p2ptrade.tests.test_agent


class TestMyReplyEProposal(unittest.TestCase):

  def test_get_data(self):
    pass # TODO check for 'etx_data'

  def test_process_reply(self):
    pass # TODO tested by ngcccbase.p2ptrade.tests.test_agent or obsolete?


class TestForeignEProposal(unittest.TestCase):

  def test_accept(self):
    pass # tested by ngcccbase.p2ptrade.tests.test_agent



if __name__ == '__main__':
  unittest.main()

