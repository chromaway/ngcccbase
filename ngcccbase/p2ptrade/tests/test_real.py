from ..ewctrl import EWalletController
from ..protocol_objects import MyEOffer, EOffer
from ..agent import EAgent

import unittest

class EchoExchangeComm:
    def __init__(self):
        self.agents = []
    def add_agent(self, agent):
        self.agents.append(agent)
    def post_message(self, content):
        print content
        for a in self.agents:
            a.dispatch_message(content)

class TestRealP2PTrade(unittest.TestCase):

    def setUp(self):
        from pwallet import PersistentWallet
        from wallet_controller import WalletController
        self.pwallet = PersistentWallet()
        self.pwallet.init_model()

    def test_real(self):
        ewctrl = EWalletController(self.pwallet.get_model())
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = EchoExchangeComm()
        agent1 = EAgent(ewctrl, config, comm)
        agent2 = EAgent(ewctrl, config, comm)

        frobla_color_desc = "obc:cc8e64cef1a880f5132e73b5a1f52a72565c92afa8ec36c445c635fe37b372fd:0:263370"
        foo_color_desc = "obc:caff27b3fe0a826b776906aceafecac7bb34af16971b8bd790170329309391ac:0:265577"

        ag1_offer = MyEOffer(
            None, 
            {"color_spec": frobla_color_desc, "value": 100},
            {"color_spec": foo_color_desc, "value": 200})
        ag2_offer = MyEOffer(
            None,
            {"color_spec": foo_color_desc, "value": 200},
            {"color_spec": frobla_color_desc, "value": 100},
            False)

        agent1.register_my_offer(ag1_offer)
        agent2.register_my_offer(ag2_offer)
        for _ in xrange(3):
            agent1.update_state()
            agent2.update_state()
        

