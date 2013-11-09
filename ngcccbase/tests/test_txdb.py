#!/usr/bin/env python

import unittest

import sqlite3

from ngcccbase import txdb

import txcons  # FIXME: will explode if not run from main directory
               #        this is a symptom of dumping stuff in the main
               #        directory, moving txcons into ngcccbase will
               #        resolve this
import utxodb  # FIXME: Same deal as txcons
import meat    # FIXME: Same as above

from coloredcoinlib import txspec

import ecdsa

from pycoin.tx.script import opcodes, tools


class TestTxDataStoreInitialization(unittest.TestCase):
    def test_initialization(self):
        connection = sqlite3.connect(":memory:")
        store = txdb.TxDataStore(connection)
        self.assertTrue(store.table_exists("tx_data"))
        self.assertTrue(store.table_exists("tx_address"))


class AddressRec(object):
    def __init__(self, meat):
        self.meat = meat


def fake_transaction(model=None):
    key = ecdsa.SigningKey.from_string(
        "\xe8\x00\xb8\xd4\xa1b\xb7o\x0f;\xf2\xcf\xca\xfd\x1a$\xb9\xa9"
        "\xeb\x0b\x08X\x9f}9C\xe4\x88\xfdD\x11b", curve=ecdsa.curves.SECP256k1)

    address = meat.Address.from_privkey(key)
    print repr(address.rawPubkey)
    print address.rawPubkey.encode("hex")
    print address.pubkey
    script = tools.compile(
        "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
            address.rawPubkey[1:-4].encode("hex"))).encode("hex")
    utxo = utxodb.UTXO("D34DB33F", 0, 1, script)
    utxo.address_rec = object()
    utxo.address_rec = AddressRec(address)
    txin = txspec.ComposedTxSpec.TxIn(utxo)
    txout = txspec.ComposedTxSpec.TxOut(1, address.pubkey)
    composed = txspec.ComposedTxSpec([txin], [txout])
    return txcons.SignedTxSpec(model, composed, False), address


class TestTxDataStore(unittest.TestCase):
    def setUp(self):
        connection = sqlite3.connect(":memory:")
        self.store = txdb.TxDataStore(connection)
        self.model = None

    def test_empty_signed_tx(self):
        transaction, address = fake_transaction(self.model)
        self.store.add_signed_tx("FAKEHASH", transaction)

        stored_id, stored_hash, stored_data, stored_status = \
            self.store.get_tx_by_hash("FAKEHASH")

        self.assertEqual(stored_hash, "FAKEHASH")
        self.assertEqual(stored_data, transaction.get_hex_tx_data())

    def test_signed_tx(self):
        transaction, address = fake_transaction(self.model)
        self.store.add_signed_tx("FAKEHASH", transaction)

        txes = self.store.get_tx_by_output_address(address.pubkey)
        (stored_hash, stored_data, stored_status) = txes.fetchone()

        self.assertEqual(stored_hash, "FAKEHASH")
        self.assertEqual(stored_data, transaction.get_hex_tx_data())
