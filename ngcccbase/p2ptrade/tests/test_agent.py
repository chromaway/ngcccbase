#!/usr/bin/env python

import time
import unittest

from ngcccbase.pwallet import PersistentWallet
from ngcccbase.wallet_controller import WalletController
from ngcccbase.p2ptrade.agent import EAgent
from ngcccbase.p2ptrade.comm import CommBase
from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.protocol_objects import MyEOffer, MyEProposal


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
        self.pwallet = PersistentWallet(None, True)
        self.pwallet.init_model()
        self.model = self.pwallet.get_model()
        adm = self.model.get_asset_definition_manager()

        # make sure you have the asset 'testobc' in your testnet.wallet !!
        self.asset = adm.get_asset_by_moniker('testobc')
        self.color_spec = self.asset.get_color_set().get_data()[0]

        self.comm0 = MockComm()
        self.comm1 = MockComm()
        self.comm0.add_peer(self.comm1)
        self.comm1.add_peer(self.comm0)
        self.wc = WalletController(self.model)
        self.ewc = EWalletController(self.model, self.wc)
        self.econfig = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        self.agent0 = EAgent(self.ewc, self.econfig, self.comm0)
        self.agent1 = EAgent(self.ewc, self.econfig, self.comm1)

        self.cv0 = { 'color_spec' : "", 'value' : 100 }
        self.cv1 = { 'color_spec' : self.color_spec, 'value' : 200 }
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

class TestP2PTradeAgent(unittest.TestCase):

    def test_fire_event(self):
      pass


if __name__ == '__main__':
    unittest.main()
