from ..ewctrl import EWalletController
from ..protocol_objects import MyEOffer, EOffer
from ..agent import EAgent
from ..comm import CommBase

from coloredcoinlib import (SimpleColorValue,
                            OBColorDefinition, UNCOLORED_MARKER)

import unittest


class MockAddressRecord(object):
    def __init__(self, address):
        self.address = address
    def get_address(self):
        return self.address

class MockWAM(object):
    def get_change_address(self, color_set):
        return MockAddressRecord('addr' + color_set.get_hash_string())
    def get_some_address(self, color_set):
        return self.get_change_address(color_set)


class MockUTXO(object):
    def __init__(self):
        self.value = 100
        self.colorvalues = [SimpleColorValue(colordef=UNCOLORED_MARKER,
                                             value=300000)]
    def get_outpoint(self):
        return ('outp1', 1)

class MockCoinQuery(object):

    def __init__(self, params):
        self.color_set = params['color_set']

    def get_result(self):
        return [MockUTXO()]

class MockColorMap(object):
    def find_color_desc(self, color_id):
        if color_id == 1:
            return 'xxx'
        elif color_id == 2:
            return 'yyy'
        else:
            return ''

    def resolve_color_desc(self, color_desc, auto_add=True):
        if color_desc == 'xxx':
            return 1
        elif color_desc == 'yyy':
            return 2
        else:
            return None

class MockModel(object):
    def get_color_map(self):
        return MockColorMap()
    def make_coin_query(self, params):
        return MockCoinQuery(params)
    def get_address_manager(self):
        return MockWAM()

class MockComm(CommBase):
    def __init__(self):
        super(MockComm, self).__init__()
        self.messages_sent = []
    def poll_and_dispatch(self):
        pass
    def post_message(self, message):
        print (message)
        self.messages_sent.append(message)
    def get_messages(self):
        return self.messages_sent

class TestMockP2PTrade(unittest.TestCase):
    def test_basic(self):
        model = MockModel()
        ewctrl = EWalletController(model, None)
        config = {"offer_expiry_interval": 30,
                  "ep_expiry_interval": 30}
        comm = MockComm()
        agent = EAgent(ewctrl, config, comm)

        # At this point the agent should not have an active proposal
        self.assertFalse(agent.has_active_ep())
        # no messages should have been sent to the network
        self.assertEqual(len(comm.get_messages()), 0)

        self.cd = OBColorDefinition(1, {'txhash': 'xxx',
                                        'outindex': 0, 'height':0})

        cv0 = SimpleColorValue(colordef=UNCOLORED_MARKER, value=100)
        cv1 = SimpleColorValue(colordef=self.cd, value=200)

        my_offer = MyEOffer(None, cv0, cv1)

        their_offer = EOffer('abcdef', cv1, cv0)

        agent.register_my_offer(my_offer)
        agent.register_their_offer(their_offer)
        agent.update()

        # Agent should have an active exchange proposal
        self.assertTrue(agent.has_active_ep())
        # Exchange proposal should have been sent over comm
        # it should be the only message, as we should not resend our offer
        # if their is an active proposal to match it
        self.assertTrue(len(comm.get_messages()), 1)
        [proposal] = comm.get_messages()
        # The offer data should be in the proposal
        their_offer_data = their_offer.get_data()
        self.assertEquals(their_offer_data, proposal["offer"])
