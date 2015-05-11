#!/usr/bin/env python

import unittest


from ngcccbase.api import Ngccc


class TestCreatetx(unittest.TestCase):

    def setUp(self):
        self.api = Ngccc(wallet="ngcccbase/tests/unittest.wallet", testnet=True)

    def test_sign_uncolored(self):
        inputs = """[{
          "outindex": "2", 
          "txid": "2ba76265f8aa68103cd3ab4da057d435917045caedabcb4904c1b0b9b42e5bef"
        }]"""
        targets = """[{
          "moniker" : "bitcoin",
          "amount" : "0.01",          
          "coloraddress" : "mtosNK4tJzrePxM7tb2V2zTxYyJUW4xx83"
        }]"""
        expected = "0100000001ef5b2eb4b9b0c10449cbabedca45709135d457a04dabd33c1068aaf86562a72b020000008a4730440220022799b32e076417c62b6d7ff3ee8c588e13dc60ba7e00ecb0f1ccc85c9dcbef022066f185a4c4d8c22764c712c4a7ffc0375cd4c186661ab74602db27f23b2598060141040e4aeac170f3c6c78696e57b1b07d14276044f1e14674ca3eddbb999b9239711f9f136902f680e2176398d6ebd3c72a5482a5ac8fc12038428ff9d59829f624bffffffff0240420f00000000001976a91491cc9812ca45e7209ff9364ce96527a7c49f1f3188ac3e770400000000001976a9142e330c36e1d0f199fd91446f2210209a0d35caef88ac00000000"
        output = self.api.createtx(inputs, targets, sign=True)
        self.assertEquals(output, expected)

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

    def test_sign_epobc(self):
        inputs = """[{
          "outindex": "1", 
          "txid": "00983ae91d3169a4e86754f277c57cf111593432820050d1430f06e6d9ef11f4"
        }]"""
        targets = """[{
          "moniker" : "fabecoin",
          "amount" : "50000",
          "coloraddress" : "nghRxMdVmnrpK@mmubnLYxcPKABKSWVyFqvYEdzKoPZBH1gZ"
        }]"""
        expected = "0100000001f411efd9e6060f43d150008232345911f17cc577f25467e8a469311de93a9800010000008b483045022100b0b10a46a2502f560161e381918816d1f9bebadae312ec49f9d3e939091adf200220050528b47165f31aa2f98029f1f0c75545077ff48bd4668e07e1ff759f4ddf79014104c55ba47261d6bca5aee2350a7e578f81e02ace331acb6bafdcfc956dffca9e02d59c32aaad764511db694e44e25313707c1749198e1c21146522ee42b74766a2330000000250c30000000000001976a914461932f048fd8a60daddc34323301781f216839a88acce250000000000001976a914fde53f69a72cac25cd4bdfe6a2a50cecdcf6050e88ac00000000"
        output = self.api.createtx(inputs, targets, sign=True)
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

    def test_sign_obc(self):
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
        expected = "01000000020f2d387962176ba88aca5898cccccc573c36b02241487ce8a30b92b238c36e64010000008a47304402201e7bf56a917f90dc8a87c21c58664283318d77eab7f0810914e3063a7bbd67b402207ce6b10796252002b9f43c23760346d130cf22268fb21997e9e48bd7233b9354014104a44feb7524b7a98ea7272c563bff183e455bf4f0ac5662533321505a01b4771ad41379c724d1f2133b4d543278cf8b9b6a47bc0c3c17bd0a0d24e2962c64fabbffffffff0f2d387962176ba88aca5898cccccc573c36b02241487ce8a30b92b238c36e64010000008a4730440220643e6b8288f0866138fef3bc4afc7d57c0597edb02589b0c47366c9a72f4c7120220588e7311e734ecce09e60751155146e4c610e4319c0c52d2b3777b911a9b2364014104a44feb7524b7a98ea7272c563bff183e455bf4f0ac5662533321505a01b4771ad41379c724d1f2133b4d543278cf8b9b6a47bc0c3c17bd0a0d24e2962c64fabbffffffff0380969800000000001976a9141075536ca2044f7db00a563f58b5f5cde182b9c588ac70415805000000001976a914b4667b33dd89990702e4adbedc6d07e3a12c91b088ac6cc5f005000000001976a9142e330c36e1d0f199fd91446f2210209a0d35caef88ac00000000"
        output = self.api.createtx(inputs, targets, sign=True)
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

