
import unittest
from coloredcoinlib import (
    ZeroSelectError, SimpleColorValue, UNCOLORED_MARKER, ColorDefinition
)
from ngcccbase.pwallet import PersistentWallet
from ngcccbase.txcons import InsufficientFundsError, RawTxSpec
from ngcccbase.wallet_controller import WalletController
from ngcccbase.p2ptrade.ewctrl import EWalletController, OperationalETxSpec
from ngcccbase.p2ptrade.protocol_objects import ETxSpec, MyEOffer


class TestEWalletController(unittest.TestCase):

    def setUp(self):
        self.pwallet = PersistentWallet(None, True)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        adm = self.model.get_asset_definition_manager()

        # make sure you have the asset 'testobc' in your testnet.wallet !!
        self.asset = adm.get_asset_by_moniker('testobc')
        self.color_spec = self.asset.get_color_set().get_data()[0]

        self.wc = WalletController(self.model)
        self.ewc = EWalletController(self.model, self.wc)

        def null(a):
            pass
        self.wc.publish_tx = null

    def test_resolve_color_spec(self):
        self.cd =self.ewc.resolve_color_spec('')
        self.assertRaises(KeyError, self.ewc.resolve_color_spec, 'nonexistent')
        self.assertTrue(isinstance(self.cd, ColorDefinition))
        self.assertEqual(self.cd.get_color_id(), 0)

    def test_select_inputs(self):
        cv = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000000000000)
        self.assertRaises(InsufficientFundsError, self.ewc.select_inputs, cv)
        
    def test_tx_spec(self):
        alice_cv = { 'color_spec' : self.color_spec, 'value' : 10 }
        bob_cv = { 'color_spec' : "", 'value' : 500 }
        alice_offer = MyEOffer(None, alice_cv, bob_cv)
        bob_offer = MyEOffer(None, bob_cv, alice_cv)
        bob_etx = self.ewc.make_etx_spec(bob_cv, alice_cv)
        self.assertTrue(isinstance(bob_etx, ETxSpec))
        for target in bob_etx.targets:
            # check address
            address = target[0]
            self.assertTrue(isinstance(address, type(u"unicode")))
            # TODO check address is correct format

            # check color_spec
            color_spec = target[1]
            self.assertTrue(isinstance(color_spec, type("str")))
            color_spec_parts = len(color_spec.split(":"))
            self.assertTrue(color_spec_parts == 4 or color_spec_parts == 1)

            # check value
            value = target[2]
            self.assertTrue(isinstance(value, type(10)))
        signed = self.ewc.make_reply_tx(bob_etx, alice_cv, bob_cv)
        self.assertTrue(isinstance(signed, RawTxSpec))

        self.ewc.publish_tx(signed, alice_offer)

        alice_etx = self.ewc.make_etx_spec(alice_cv, bob_cv)
        self.assertTrue(isinstance(alice_etx, ETxSpec))
        for target in alice_etx.targets:
            # check address
            address = target[0]
            self.assertTrue(isinstance(address, type(u"unicode")))
            # TODO check address is correct format

            # check color_spec
            color_spec = target[1]
            self.assertTrue(isinstance(color_spec, type("str")))
            color_spec_parts = len(color_spec.split(":"))
            self.assertTrue(color_spec_parts == 4 or color_spec_parts == 1)

            # check value
            value = target[2]
            self.assertTrue(isinstance(value, type(10)))
        signed = self.ewc.make_reply_tx(alice_etx, bob_cv, alice_cv)
        self.assertTrue(isinstance(signed, RawTxSpec))

        oets = OperationalETxSpec(self.model, self.ewc)
        oets.set_our_value_limit(bob_cv)
        oets.prepare_inputs(alice_etx)
        zero = SimpleColorValue(colordef=UNCOLORED_MARKER, value=0)
        self.assertRaises(ZeroSelectError, oets.select_coins, zero)
        toomuch = SimpleColorValue(colordef=UNCOLORED_MARKER, value=10000000000000)
        self.assertRaises(InsufficientFundsError, oets.select_coins, toomuch)

if __name__ == '__main__':
    unittest.main()
