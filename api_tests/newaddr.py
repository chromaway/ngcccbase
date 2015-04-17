#!/usr/bin/env python

import unittest
import pyjsonrpc
import bitcoinaddress

class TestRealP2PTrade(unittest.TestCase):

  def setUp(self):
    self.rpc = pyjsonrpc.HttpClient(url = "http://localhost:8080")

  def test_newaddr_valid_bitcoin_address(self):
    address =  self.rpc.newaddr("bitcoin")
    self.assertTrue(bitcoinaddress.validate(address))

  def test_newaddr_non_repeating(self):
    address_a =  self.rpc.newaddr("bitcoin")
    address_b =  self.rpc.newaddr("bitcoin")
    address_c =  self.rpc.newaddr("bitcoin")
    self.assertTrue(len(set([address_a, address_b, address_c])) == 3)

  def test_newaddr_non_existing_asset(self):
    try:
      self.rpc.newaddr("non_existing_asset")
    except pyjsonrpc.JsonRpcError as error:
      self.assertEqual(error.code, 32602) # invalid params error code

  # TODO test colored

if __name__ == '__main__':
  unittest.main()

