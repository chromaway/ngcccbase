#!/usr/bin/env python

import unittest
import pyjsonrpc
import bitcoinaddress

class TestRealP2PTrade(unittest.TestCase):

  def setUp(self):
    self.rpc = pyjsonrpc.HttpClient(
      url = "http://localhost:8080",
      username = "Username",
      password = "Password"
    )

  def test_newaddr_valid_bitcoin_address(self):
    address =  self.rpc.newaddr("bitcoin")
    self.assertTrue(bitcoinaddress.validate(address))

  def test_newaddr_non_repeating(self):
    address_a =  self.rpc.newaddr("bitcoin")
    address_b =  self.rpc.newaddr("bitcoin")
    self.assertTrue(address_a != address_b)

  # TODO test uncolored
  # TODO test address not used

if __name__ == '__main__':
  unittest.main()

