#!/usr/bin/env python

import unittest

from ngcccbase.p2ptrade.ewctrl import EWalletController
from ngcccbase.p2ptrade.protocol_objects import MyEOffer, EOffer
from ngcccbase.p2ptrade.agent import EAgent

class MockComm(object):
    def __init__(self):
        self.agents = []
        self.peers = []
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


class TestRealP2PTrade(unittest.TestCase):

    def setUp(self):
        from ngcccbase.pwallet import PersistentWallet
        from ngcccbase.wallet_controller import WalletController
        self.pwallet = PersistentWallet()
        self.pwallet.init_model()
        self.wctrl = WalletController(self.pwallet.wallet_model)

    def test_real(self):
        ewctrl = EWalletController(self.pwallet.get_model(), self.wctrl)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm1 = MockComm()
        comm2 = MockComm()
        comm1.add_peer(comm2)
        comm2.add_peer(comm1)
        agent1 = EAgent(ewctrl, config, comm1)
        agent2 = EAgent(ewctrl, config, comm2)

        frobla_color_desc = "obc:cc8e64cef1a880f5132e73b5a1f52a72565c92afa8ec36c445c635fe37b372fd:0:263370"
        foo_color_desc = "obc:caff27b3fe0a826b776906aceafecac7bb34af16971b8bd790170329309391ac:0:265577"

        self.cd0 = OBColorDefinition(1, {'txhash': 'cc8e64cef1a880f5132e73b5a1f52a72565c92afa8ec36c445c635fe37b372fd',
                                         'outindex': 0, 'height':263370})

        self.cd1 = OBColorDefinition(1, {'txhash': 'caff27b3fe0a826b776906aceafecac7bb34af16971b8bd790170329309391ac',
                                         'outindex': 0, 'height':265577})

        cv0 = SimpleColorValue(colordef=self.cd0, value=100)
        cv1 = SimpleColorValue(colordef=self.cd1, value=200)

        ag1_offer = MyEOffer(None, cv0, cv1)
        ag2_offer = MyEOffer(None, cv0, cv1, False)

        agent1.register_my_offer(ag1_offer)
        agent2.register_my_offer(ag2_offer)
        for _ in xrange(3):
            agent1._update_state()
            agent2._update_state()
        

if __name__ == '__main__':
    unittest.main()
