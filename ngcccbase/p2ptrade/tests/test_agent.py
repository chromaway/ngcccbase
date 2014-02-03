#!/usr/bin/env python

import time
import unittest

from coloredcoinlib import (SimpleColorValue, UNCOLORED_MARKER, ColorDefinition,
                            AidedColorDataBuilder, ThinColorData,
                            InvalidColorIdError, ZeroSelectError,
                            OBColorDefinition, ColorDataBuilderManager)

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController

from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import CommBase
from ngcccbase.p2ptrade.ewctrl import EWalletController, OperationalETxSpec
from ngcccbase.p2ptrade.protocol_objects import MyEOffer, EOffer, MyEProposal


class MockComm(CommBase):
    def __init__(self):
        super(MockComm, self).__init__()
        self.agents = []
        self.peers = []
        self.messages_sent = []
    def poll_and_dispatch(self):
        pass
    def add_agent(self, agent):
        self.agents.append(agent)
    def add_peer(self, peer):
        self.peers.append(peer)
    def post_message(self, content):
        print (content)
        for peer in self.peers:
            peer.process_message(content)
    def process_message(self, content):
        for agent in self.agents:
            agent.dispatch_message(content)
        self.messages_sent.append(content)
    def get_messages(self):
        return self.messages_sent


class TestAgent(unittest.TestCase):
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
        self.econfig = {"offer_expiry_interval": 30,
                        "ep_expiry_interval": 30}
        self.comm0 = MockComm()
        self.comm1 = MockComm()
        self.comm0.add_peer(self.comm1)
        self.comm1.add_peer(self.comm0)
        self.agent0 = EAgent(self.ewc, self.econfig, self.comm0)
        self.agent1 = EAgent(self.ewc, self.econfig, self.comm1)
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
        def null(a):
            pass
        self.wc.publish_tx = null
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

        self.cd = ColorDefinition.from_color_desc(1, self.cspec)

        self.cv0 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=100)
        self.cv1 = SimpleColorValue(colordef=self.cd, value=200)

        self.offer0 = MyEOffer(None, self.cv0, self.cv1)
        self.offer1 = MyEOffer(None, self.cv1, self.cv0)

    def test_set_event_handler(self):
        tmp = { 'test': 0}
        def handler(val):
            tmp['test'] = val
        self.agent0.set_event_handler('click', handler)
        self.agent0.fire_event('click', 7)
        self.assertEqual(tmp['test'], 7)
        self.agent0.ep_timeout = time.time() - 100
        self.assertFalse(self.agent0.has_active_ep())

    def test_real(self):
        self.add_coins()
        self.assertFalse(self.agent0.has_active_ep())
        self.agent0.register_my_offer(self.offer0)
        self.agent1.register_my_offer(self.offer1)
        for i in range(3):
            self.agent0._update_state()
            self.agent1._update_state()
        self.assertFalse(self.agent0.has_active_ep())
        self.assertFalse(self.agent1.has_active_ep())

        m0 = self.comm0.get_messages()
        m1 = self.comm1.get_messages()
        self.assertEquals(len(m0), 2)
        self.assertEquals(len(m1), 2)

        self.assertEquals(self.offer0.get_data(), m0[1]['offer'])
        self.assertEquals(self.offer0.get_data(), m1[1]['offer'])
        # expire offers
        offer2 = MyEOffer(None, self.cv0, self.cv1)

        self.agent0.register_my_offer(offer2)
        self.agent0.update()
        self.agent0.update()
        self.agent1.update()
        self.agent0.cancel_my_offer(offer2)
        self.agent0.update()
        self.agent1.update()
        self.assertFalse(self.agent0.has_active_ep())
        self.assertFalse(self.agent1.has_active_ep())

        offer3 = MyEOffer(None, self.cv1, self.cv0)
        self.agent0.make_exchange_proposal(offer3, offer2)
        self.assertRaises(Exception, self.agent0.make_exchange_proposal,
                          offer3, offer2)
        ep = MyEProposal(self.ewc, offer3, offer2)
        def raiseException(x):
            raise Exception()
        self.agent0.set_event_handler('accept_ep', raiseException)

        # methods that should do nothing now that we have an active ep
        self.agent0.accept_exchange_proposal(ep)
        self.agent0.match_offers()

        self.agent0.register_their_offer(offer3)
        self.agent0.accept_exchange_proposal(ep)
        ep2 = MyEProposal(self.ewc, offer3, offer2)
        self.agent0.dispatch_exchange_proposal(ep2.get_data())

        # test a few corner cases
        self.agent0.register_my_offer(offer2)
        offer2.refresh(-1000)
        self.assertTrue(offer2.expired())
        self.agent0.service_my_offers()
        self.agent0.cancel_my_offer(offer2)
        self.agent0.register_their_offer(offer3)
        offer3.refresh(-1000)
        self.agent0.service_their_offers()


if __name__ == '__main__':
    unittest.main()
