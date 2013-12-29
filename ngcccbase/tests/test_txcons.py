#!/usr/bin/env python

import os
import unittest

from pycoin.tx.script import opcodes, tools

from coloredcoinlib import (OBColorDefinition, ColorSet,
                            SimpleColorValue, ColorTarget, InvalidColorIdError,
                            UNCOLORED_MARKER, ZeroSelectError)

from ngcccbase.asset import AssetDefinition, AdditiveAssetValue, AssetTarget
from ngcccbase.txcons import (InvalidTargetError, InvalidTransformationError, 
                              InsufficientFundsError, BasicTxSpec,
                              SimpleOperationalTxSpec, RawTxSpec,
                              TransactionSpecTransformer)
from ngcccbase.pwallet import PersistentWallet



class TestTxcons(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.pwallet = PersistentWallet(self.path)
        self.config = {'dw_master_key': 'test', 'testnet': True, 'ccc': {
                'colordb_path' : self.path}, 'bip0032': False }
        self.pwallet.wallet_config = self.config
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.colormap = self.model.get_color_map()

        self.colordesc0 = "obc:color0:0:0"
        self.colordesc1 = "obc:color1:0:0"
        self.colordesc2 = "obc:color2:0:0"

        # add some colordescs
        self.colorid0 = self.colormap.resolve_color_desc(self.colordesc0)
        self.colorid1 = self.colormap.resolve_color_desc(self.colordesc1)
        self.colorid2 = self.colormap.resolve_color_desc(self.colordesc2)

        self.colordef0 = OBColorDefinition(
            self.colorid0, {'txhash': 'color0', 'outindex': 0})
        self.colordef1 = OBColorDefinition(
            self.colorid1, {'txhash': 'color1', 'outindex': 0})
        self.colordef2 = OBColorDefinition(
            self.colorid2, {'txhash': 'color2', 'outindex': 0})

        self.asset_config = {
            'monikers': ['blue'],
            'color_set': [self.colordesc0],
            }
        self.basset_config = {
            'monikers': ['bitcoin'],
            'color_set': [''],
            }
        self.asset = AssetDefinition(self.colormap, self.asset_config)
        self.basset = AssetDefinition(self.colormap, self.basset_config)
        self.basic = BasicTxSpec(self.model)
        self.bbasic = BasicTxSpec(self.model)

        wam = self.model.get_address_manager()
        self.address0 = wam.get_new_address(self.asset.get_color_set())
        self.addr0 = self.address0.get_address()

        self.bcolorset = ColorSet(self.colormap, [''])
        self.baddress = wam.get_new_address(self.bcolorset)
        self.baddr = self.baddress.get_address()

        self.assetvalue0 = AdditiveAssetValue(asset=self.asset, value=5)
        self.assetvalue1 = AdditiveAssetValue(asset=self.asset, value=6)
        self.assetvalue2 = AdditiveAssetValue(asset=self.asset, value=7)
        self.bassetvalue = AdditiveAssetValue(asset=self.basset, value=8)
        self.assettarget0 = AssetTarget(self.addr0, self.assetvalue0)
        self.assettarget1 = AssetTarget(self.addr0, self.assetvalue1)
        self.assettarget2 = AssetTarget(self.addr0, self.assetvalue2)
        self.bassettarget = AssetTarget(self.baddr, self.bassetvalue)

        self.atargets = [self.assettarget0, self.assettarget1, self.assettarget2]

        # add some targets
        self.colorvalue0 = SimpleColorValue(colordef=self.colordef0, value=5)
        self.colortarget0 = ColorTarget(self.addr0, self.colorvalue0)
        self.colorvalue1 = SimpleColorValue(colordef=self.colordef0, value=6)
        self.colortarget1 = ColorTarget(self.addr0, self.colorvalue1)
        self.colorvalue2 = SimpleColorValue(colordef=self.colordef0, value=7)
        self.colortarget2 = ColorTarget(self.addr0, self.colorvalue2)
        self.bcolorvalue = SimpleColorValue(colordef=UNCOLORED_MARKER, value=8)
        self.bcolortarget = ColorTarget(self.baddr, self.bcolorvalue)

        self.targets = [self.colortarget0, self.colortarget1,
                        self.colortarget2]
        self.transformer = TransactionSpecTransformer(self.model, self.config)
        self.blockhash = '00000000c927c5d0ee1ca362f912f83c462f644e695337ce3731b9f7c5d1ca8c'
        self.txhash = '4fe45a5ba31bab1e244114c4555d9070044c73c98636231c77657022d76b87f7'

    def test_basic(self):
        self.assertRaises(InvalidTargetError, self.basic.is_monocolor)
        self.assertRaises(InvalidTargetError,
                          self.basic.add_target, self.colortarget0)
        self.basic.add_target(self.assettarget0)
        self.basic.add_target(self.assettarget1)
        self.basic.add_target(self.assettarget2)
        self.assertEqual(self.basic.is_monocolor(), True)
        self.assertEqual(self.basic.is_monoasset(), True)
        self.assertEqual(self.basic.targets, self.atargets)
        self.basic.add_target(self.bassettarget)
        self.assertEqual(self.basic.is_monoasset(), False)
        self.assertEqual(self.basic.is_monocolor(), False)
        self.assertRaises(InvalidTransformationError,
                          self.basic.make_operational_tx_spec, self.asset)

    def add_coins(self):
        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.address0.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.addr0, self.txhash,
                                           0, 100, script)

        script = tools.compile(
            "OP_DUP OP_HASH160 {0} OP_EQUALVERIFY OP_CHECKSIG".format(
                self.baddress.rawPubkey().encode("hex"))).encode("hex")

        self.model.utxo_man.store.add_utxo(self.baddr, self.txhash,
                                           1, 20000, script)
        self.model.ccc.metastore.set_as_scanned(self.colorid0, self.blockhash)
        self.model.ccc.cdstore.add(self.colorid0, self.txhash, 0, 100, '')


    def test_operational(self):
        self.basic.add_target(self.assettarget0)
        self.basic.add_target(self.assettarget1)
        self.basic.add_target(self.assettarget2)
        op = self.transformer.transform_basic(self.basic, 'operational')
        self.assertTrue(self.transformer.classify_tx_spec(op), 'operational')
        self.assertRaises(InvalidTargetError, op.add_target, 1)
        self.assertEqual(ColorTarget.sum(op.get_targets()),
                         ColorTarget.sum(self.targets))
        self.assertEqual(op.get_change_addr(self.colordef0), self.addr0)
        self.assertEqual(op.get_change_addr(UNCOLORED_MARKER), self.baddr)
        self.assertEqual(op.get_required_fee(1).get_value(), 10000)
        self.assertRaises(InvalidColorIdError, op.get_change_addr,
                          self.colordef1)
        cv = SimpleColorValue(colordef=self.colordef0, value=0)
        self.assertRaises(ZeroSelectError, op.select_coins, cv)
        cv = SimpleColorValue(colordef=self.colordef0, value=5)
        self.assertRaises(InsufficientFundsError, op.select_coins, cv)
        self.add_coins()
        self.assertEqual(op.select_coins(cv)[1].get_value(), 100)


    def test_composed(self):
        self.basic.add_target(self.assettarget0)
        self.basic.add_target(self.assettarget1)
        self.basic.add_target(self.assettarget2)
        self.add_coins()
        op = self.transformer.transform(self.basic, 'operational')
        self.assertEqual(op.get_change_addr(self.colordef0), self.addr0)
        self.assertEqual(op.get_change_addr(UNCOLORED_MARKER), self.baddr)
        comp = self.transformer.transform(op, 'composed')
        self.assertTrue(self.transformer.classify_tx_spec(comp), 'composed')
        signed = self.transformer.transform(comp, 'signed')
        self.assertTrue(self.transformer.classify_tx_spec(signed), 'signed')
        self.assertEqual(len(signed.get_hex_txhash()), 64)
        txdata = signed.get_tx_data()
        same = RawTxSpec.from_tx_data(self.model, txdata)
        self.assertEqual(same.get_hex_tx_data(), signed.get_hex_tx_data())
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform,
                          signed, '')

    def test_other(self):
        self.assertEqual(self.transformer.classify_tx_spec(1), None)
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_basic,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_operational,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_composed,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform_signed,
                          self.basic, '')
        self.assertRaises(InvalidTransformationError,
                          self.transformer.transform,
                          '', '')
        self.add_coins()
        self.bbasic.add_target(self.bassettarget)
        signed = self.transformer.transform(self.bbasic, 'signed')
        self.assertEqual(len(signed.get_hex_txhash()), 64)


if __name__ == '__main__':
    unittest.main()
