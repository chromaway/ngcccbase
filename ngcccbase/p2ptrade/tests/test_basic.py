from ..ewctrl import EWalletController
from ..protocol_objects import MyEOffer, EOffer
from ..agent import EAgent

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

class MockWalletController(object):
    def __init__(self, model):
        self.model = model

    def get_model(self):
        return self.model

class MockUTXO(object):
    def __init__(self):
        self.value = 100
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

class MockComm(object):
    def post_message(self, message):
        print message

def test():
    model = MockModel()
    m_ctrl = MockWalletController(model)
    ewctrl = EWalletController(m_ctrl)
    config = {"offer_expiry_interval": 30,
              "ep_expiry_interval": 30}
    agent = EAgent(ewctrl, config, MockComm())
    agent.register_my_offer(
        MyEOffer(None, 
                 {"color_spec": "xxx", "value": 100},
                 {"color_spec": "yyy", "value": 200}))
    agent.register_their_offer(
        EOffer('abcdef', 
               {"color_spec": "yyy", "value": 200},
               {"color_spec": "xxx", "value": 100}))
    agent.update_state()
             
