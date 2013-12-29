#!/usr/bin/env python

import unittest

from coloredcoinlib import (ColorSet, ColorDataBuilderManager, ColorTarget,
                            AidedColorDataBuilder, ThinColorData,
                            InvalidColorIdError, ZeroSelectError,
                            SimpleColorValue, UNCOLORED_MARKER)

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.txcons import InsufficientFundsError, RawTxSpec
from ngcccbase.wallet_controller import WalletController

from ngcccbase.p2ptrade.ewctrl import EWalletController, OperationalETxSpec
from ngcccbase.p2ptrade.protocol_objects import ETxSpec


class TestEWalletController(unittest.TestCase):

    def setUp(self):
        self.path = ":memory:"
        self.config = {
            'hdw_master_key':
                '91813223e97697c42f05e54b3a85bae601f04526c5c053ff0811747db77cfdf5f1accb50b3765377c379379cd5aa512c38bf24a57e4173ef592305d16314a0f4',
            'testnet': True,
            'ccc': {'colordb_path' : self.path},
            }
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.wc = WalletController(self.model)

        self.ewc = EWalletController(self.model, self.wc)
        self.bcolorset =self.ewc.resolve_color_spec('')
        self.cspec = "obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"

    def add_coins(self):
        self.config['asset_definitions'] = [
            {"color_set": [""], "monikers": ["bitcoin"], "unit": 100000000},  
            {"color_set": [self.cspec], "monikers": ['test'], "unit": 1},]
        self.config['hdwam'] = {
            "genesis_color_sets": [ 
                [self.cspec],
                ],
            "color_set_states": [
                {"color_set": [""], "max_index": 1},
                {"color_set": [self.cspec], "max_index": 7},
                ]
            }
        self.config['bip0032'] = True
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        self.ewc.model = self.model
        self.wc.model = self.model
        # modify model colored coin context, so test runs faster
        ccc = self.model.ccc
        cdbuilder = ColorDataBuilderManager(
            ccc.colormap, ccc.blockchain_state, ccc.cdstore,
            ccc.metastore, AidedColorDataBuilder)

        ccc.colordata = ThinColorData(
            cdbuilder, ccc.blockchain_state, ccc.cdstore, ccc.colormap)

        # need to query the blockchain
        self.model.utxo_man.update_all()

        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker('test')
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()


    def test_resolve_color_spec(self):
        self.assertRaises(InvalidColorIdError,
                          self.ewc.resolve_color_spec, 'nonexistent')
        self.assertTrue(isinstance(self.bcolorset, ColorSet))
        self.assertEqual(self.bcolorset.color_id_set, set([0]))

    def test_select_inputs(self):
        cv = SimpleColorValue(colordef=UNCOLORED_MARKER, value=1)
        self.assertRaises(InsufficientFundsError, self.ewc.select_inputs, cv)
        
    def test_tx_spec(self):
        self.add_colors()

        our = SimpleColorValue(colordef=UNCOLORED_MARKER, value=500)
        colormap = self.model.get_color_map()
        colordef = colormap.get_color_def(self.cspec)
        their = SimpleColorValue(colordef=colordef, value=10)
        etx = self.ewc.make_etx_spec(our, their)
        self.assertTrue(isinstance(etx, ETxSpec))
        for target in etx.targets:
            self.assertTrue(isinstance(target, ColorTarget))
        signed = self.ewc.make_reply_tx(etx, our, their)
        self.assertTrue(isinstance(signed, RawTxSpec))

        self.ewc.publish_tx(signed)

        etx = self.ewc.make_etx_spec(their, our)
        self.assertTrue(isinstance(etx, ETxSpec))
        for target in etx.targets:
            self.assertTrue(isinstance(target, ColorTarget))
        signed = self.ewc.make_reply_tx(etx, their, our)
        self.assertTrue(isinstance(signed, RawTxSpec))

        oets = OperationalETxSpec(self.model, self.ewc)
        zero = SimpleColorValue(colordef=UNCOLORED_MARKER, value=0)
        self.assertRaises(ZeroSelectError, oets.select_coins, zero)
        toomuch = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000000000000)
        self.assertRaises(InsufficientFundsError, oets.select_coins, toomuch)

        


if __name__ == '__main__':
    unittest.main()
