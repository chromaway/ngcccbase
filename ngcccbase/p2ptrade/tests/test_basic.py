from ewctrl import EWalletController
from protocol_objects import MyEOffer
from agent import EAgent


class MockWalletController(object):
    def __init__(self, model):
        self.model = model

    def get_model(self):
        return self.model

class MockModel(object):
    pass

def test():
    model = MockModel()
    m_ctrl = MockWalletController(model)
    ewctrl = EWalletController(m_ctrl)
    agent = EAgent(ewctrl, {}, None)
    agent.register_my_offer(
        MyEOffer(None, 
                 {"color_spec": "xxx", "value": 100},
                 {"color_spec": "yyy", "value": 200}))
    agent.update_state()
             
