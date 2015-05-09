#!/usr/bin/env python

import unittest


from ngcccbase.api import Ngccc


class TestCreatetx(unittest.TestCase):

    def setUp(self):
        self.api = Ngccc(wallet="ngcccbase/tests/unittest.wallet", testnet=True)

    def test_uncolored(self):
        inputs = """[{
          "outindex": "2", 
          "txid": "2ba76265f8aa68103cd3ab4da057d435917045caedabcb4904c1b0b9b42e5bef"
        }]"""
        targets = """[{
          "moniker" : "bitcoin",
          "amount" : "0.01",          
          "coloraddress" : "mtosNK4tJzrePxM7tb2V2zTxYyJUW4xx83"
        }]"""
        expected = "0100000001ef5b2eb4b9b0c10449cbabedca45709135d457a04dabd33c1068aaf86562a72b0200000000ffffffff0240420f00000000001976a91491cc9812ca45e7209ff9364ce96527a7c49f1f3188ac3e770400000000001976a9142e330c36e1d0f199fd91446f2210209a0d35caef88ac00000000"
        output = self.api.createtx(inputs, targets)
        self.assertEquals(output, expected)

    def test_epobc(self):
        inputs = """[{
          "outindex": "1", 
          "txid": "00983ae91d3169a4e86754f277c57cf111593432820050d1430f06e6d9ef11f4"
        }]"""
        targets = """[{
          "moniker" : "fabecoin",
          "amount" : "50000",
          "coloraddress" : "nghRxMdVmnrpK@mmubnLYxcPKABKSWVyFqvYEdzKoPZBH1gZ"
        }]"""
        expected = "0100000001f411efd9e6060f43d150008232345911f17cc577f25467e8a469311de93a98000100000000330000000250c30000000000001976a914461932f048fd8a60daddc34323301781f216839a88acce250000000000001976a914fde53f69a72cac25cd4bdfe6a2a50cecdcf6050e88ac00000000"
        output = self.api.createtx(inputs, targets)
        self.assertEquals(output, expected)

    def test_obc(self):
        inputs = """[{
          "outindex": "1", 
          "txid": "646ec338b2920ba3e87c484122b0363c57cccccc9858ca8aa86b176279382d0f"
        }]"""
        targets = """[{
          "moniker" : "bronze",
          "amount" : "0.1",
          "coloraddress" : "7TR9SB6nKw81cw@mh1yf4uNmedzaJLfLKkYWUyvHAeEo13rLG"
        }]"""
        # FIXME why three outputs ?
        expected = "01000000020f2d387962176ba88aca5898cccccc573c36b02241487ce8a30b92b238c36e640100000000ffffffff0f2d387962176ba88aca5898cccccc573c36b02241487ce8a30b92b238c36e640100000000ffffffff0380969800000000001976a9141075536ca2044f7db00a563f58b5f5cde182b9c588ac70415805000000001976a914b4667b33dd89990702e4adbedc6d07e3a12c91b088ac6cc5f005000000001976a9142e330c36e1d0f199fd91446f2210209a0d35caef88ac00000000"
        output = self.api.createtx(inputs, targets)
        self.assertEquals(output, expected)


class TestTxoutvalue(unittest.TestCase):

    def setUp(self):
        self.api = Ngccc(wallet="ngcccbase/tests/unittest.wallet", testnet=True)
    
    def test_uncolored(self):
        txid = "2ba76265f8aa68103cd3ab4da057d435917045caedabcb4904c1b0b9b42e5bef"
        outindex = 2
        moniker = "bitcoin"
        expected = { "bitcoin": "0.0129526" }
        output = self.api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_obc(self):
        txid = "646ec338b2920ba3e87c484122b0363c57cccccc9858ca8aa86b176279382d0f"
        outindex = 1
        moniker = "bronze"
        expected = { "bronze": "0.9967" }
        output = self.api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_zero_obc(self):
        txid = "00983ae91d3169a4e86754f277c57cf111593432820050d1430f06e6d9ef11f4"
        outindex = 1
        moniker = "bronze"
        expected = { "bronze": "0" }
        output = self.api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_epobc(self):
        txid = "00983ae91d3169a4e86754f277c57cf111593432820050d1430f06e6d9ef11f4"
        outindex = 1
        moniker = "fabecoin"
        expected = { "fabecoin": "59678" }
        output = self.api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

    def test_zero_epobc(self):
        txid = "646ec338b2920ba3e87c484122b0363c57cccccc9858ca8aa86b176279382d0f"
        outindex = 1
        moniker = "fabecoin"
        expected = { "fabecoin": "0" }
        output = self.api.txoutvalue(txid, outindex, moniker)
        self.assertEquals(output, expected)

if __name__ == '__main__':
    unittest.main()

