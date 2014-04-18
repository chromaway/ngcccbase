#!/usr/bin/env python

import unittest

from ngcccbase.verifier import Verifier, hash_decode
from ngcccbase.services.electrum import (
    ElectrumInterface, EnhancedBlockchainState)

class FakeBlockchainState(object):
    def get_height(self):
        return 100

    def get_merkle(self, tx_hash):
        l = ["3a459eab5f0cf8394a21e04d2ed3b2beeaa59795912e20b9c680e9db74dfb18c",
             "f6ae335dc2d2aecb6a255ebd03caaf6820e6c0534531051066810080e0d822c8",
             "15eca0aa3e2cc2b9b4fbe0629f1dda87f329500fcdcd6ef546d163211266b3b3"]
        return {'merkle': l, 'block_height': 99, 'pos': 1}

    def get_header(self, tx_hash):
        r = "9cdf7722eb64015731ba9794e32bdefd9cf69b42456d31f5e59aedb68c57ed52"
        return {'merkle_root': r, 'timestamp': 123}

class TestVerifier(unittest.TestCase):

    def setUp(self):
        fake_blockchain_state = FakeBlockchainState()
        self.verifier = Verifier(fake_blockchain_state)

    def test_get_confirmations(self):
        self.verifier.verified_tx['test'] = (95, 111, 1)
        self.assertEqual(self.verifier.get_confirmations('test'), 6)
        self.verifier.verified_tx['test'] = (101, 111, 1)
        self.assertEqual(self.verifier.get_confirmations('test'), 0)
        self.assertEqual(self.verifier.get_confirmations(''), None)
        del self.verifier.verified_tx['test']

    def test_get_merkle_root(self):
        # r = root, s = start, l = merkle hash list
        r = "56dee62283a06e85e182e2d0b421aceb0eadec3d5f86cdadf9688fc095b72510"
        self.assertEqual(self.verifier.get_merkle_root([], r, 0), r)

        # example from pycoin/merkle.py
        r = "30325a06daadcefb0a3d1fe0b6112bb6dfef794316751afc63f567aef94bd5c8"
        s = "67ffe41e53534805fb6883b4708fd3744358f99e99bc52111e7a17248effebee"
        l = ["c8b336acfc22d66edf6634ce095b888fe6d16810d9c85aff4d6641982c2499d1"]
        self.assertEqual(self.verifier.get_merkle_root(l, s, 0), r)

        # example from here: https://bitcointalk.org/index.php?topic=44707.0
        r = "9cdf7722eb64015731ba9794e32bdefd9cf69b42456d31f5e59aedb68c57ed52"
        s = "be38f46f0eccba72416aed715851fd07b881ffb7928b7622847314588e06a6b7"
        l = ["3a459eab5f0cf8394a21e04d2ed3b2beeaa59795912e20b9c680e9db74dfb18c",
             "f6ae335dc2d2aecb6a255ebd03caaf6820e6c0534531051066810080e0d822c8",
             "15eca0aa3e2cc2b9b4fbe0629f1dda87f329500fcdcd6ef546d163211266b3b3"]
        self.assertEqual(self.verifier.get_merkle_root(l, s, 1), r)
        s = "59d1e83e5268bbb491234ff23cbbf2a7c0aa87df553484afee9e82385fc7052f"
        l = ["d173f2a12b6ff63a77d9fe7bbb590bdb02b826d07739f90ebb016dc9297332be",
             "13a3595f2610c8e4d727130daade66c772fdec4bd2463d773fd0f85c20ced32d",
             "15eca0aa3e2cc2b9b4fbe0629f1dda87f329500fcdcd6ef546d163211266b3b3"]
        self.assertEqual(self.verifier.get_merkle_root(l, s, 3), r)

    def test_verify_merkle(self):
        h = "be38f46f0eccba72416aed715851fd07b881ffb7928b7622847314588e06a6b7"
        self.verifier.verify_merkle(h)
        self.assertEqual(self.verifier.get_confirmations(h), 2)

    def test_random_merkle(self):
        server_url = "electrum.pdmc.net"
        ei = ElectrumInterface(server_url, 50001)
        bcs = EnhancedBlockchainState(server_url, 50001)
        self.verifier.blockchain_state = bcs
        h = '265db1bc122c4dae20dd0b55d55c7b270fb1378054fe624457b73bc28b5edd55'
        self.verifier.verify_merkle(h)
        self.assertTrue(self.verifier.get_confirmations(h) > 3)


if __name__ == '__main__':
    unittest.main()
