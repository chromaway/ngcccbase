#!/usr/bin/env python

import unittest

from coloredcoinlib import (ColorSet, ColorDataBuilderManager,
                            AidedColorDataBuilder, ThinColorData)

from ngcccbase.deterministic import DWalletAddressManager
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.txcons import BasicTxSpec, InvalidTargetError
from ngcccbase.txdb import TxDb
from ngcccbase.utxodb import UTXOQuery
from ngcccbase.wallet_model import CoinQueryFactory
from ngcccbase.wallet_controller import WalletController


class TestWalletModel(unittest.TestCase):

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
        self.colormap = self.model.get_color_map()
        self.bcolorset = ColorSet(self.colormap, [''])
        self.basset = self.model.get_asset_definition_manager(
            ).get_asset_by_moniker('bitcoin')
        self.cqf = self.model.get_coin_query_factory()

    def test_get_tx_db(self):
        self.assertTrue(isinstance(self.model.get_tx_db(), TxDb))

    def test_is_testnet(self):
        self.assertTrue(self.model.is_testnet())

    def test_get_coin_query_factory(self):
        self.assertTrue(isinstance(self.cqf, CoinQueryFactory))
        self.cqf.make_query({'color_set': self.bcolorset})
        self.cqf.make_query({'color_id_set': self.bcolorset.color_id_set})
        self.cqf.make_query({'asset': self.basset})
        self.assertRaises(Exception, self.cqf.make_query, {})

    def test_transform(self):
        tx_spec = BasicTxSpec(self.model)
        self.assertRaises(InvalidTargetError,
                          self.model.transform_tx_spec, tx_spec, 'signed')

    def test_make_query(self):
        q = self.model.make_coin_query({'color_set': self.bcolorset})
        self.assertTrue(isinstance(q, UTXOQuery))

    def test_get_address_manager(self):
        m = self.model.get_address_manager()
        self.assertTrue(issubclass(m.__class__, DWalletAddressManager))

    def test_get_history(self):
        self.config['asset_definitions'] = [
            {"color_set": [""], "monikers": ["bitcoin"], "unit": 100000000},  
            {"color_set": ["obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"], "monikers": ['test'], "unit": 1},]
        self.config['hdwam'] = {
            "genesis_color_sets": [ 
                ["obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"],
                ],
            "color_set_states": [
                {"color_set": [""], "max_index": 1},
                {"color_set": ["obc:03524a4d6492e8d43cb6f3906a99be5a1bcd93916241f759812828b301f25a6c:0:153267"], "max_index": 7},
                ]
            }
        self.config['bip0032'] = True
        self.pwallet = PersistentWallet(self.path, self.config)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        # modify model colored coin context, so test runs faster
        ccc = self.model.ccc
        cdbuilder = ColorDataBuilderManager(
            ccc.colormap, ccc.blockchain_state, ccc.cdstore,
            ccc.metastore, AidedColorDataBuilder)

        ccc.colordata = ThinColorData(
            cdbuilder, ccc.blockchain_state, ccc.cdstore, ccc.colormap)

        wc = WalletController(self.model)

        adm = self.model.get_asset_definition_manager()
        asset = adm.get_asset_by_moniker('test')
        self.model.utxo_man.update_all()
        cq = self.model.make_coin_query({"asset": asset})
        utxo_list = cq.get_result()

        # send to the second address so the mempool has something
        addrs = wc.get_all_addresses(asset)
        wc.send_coins(asset, [addrs[1].get_color_address()], [1000])

        history = self.model.get_history_for_asset(asset)
        self.assertTrue(len(history) > 30)


if __name__ == '__main__':
    unittest.main()
