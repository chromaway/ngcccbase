import time

from coloredcoinlib import IncompatibleTypesError
from ngcccbase.txcons import RawTxSpec

from utils import make_random_id


class EOffer(object):
    """
    A is the offer side's ColorValue
    B is the replyer side's ColorValue
    """
    def __init__(self, oid, A, B):
        self.oid = oid or make_random_id()
        self.A = A
        self.B = B
        self.expires = None

    def expired(self, shift=0):
        return (not self.expires) or (self.expires < time.time() + shift)

    def refresh(self, delta):
        self.expires = time.time() + delta

    def get_data(self):
        return {"oid": self.oid,
                "A": self.A,
                "B": self.B}

    def matches(self, offer):
        """A <=x=> B"""
        return self.A == offer.B and offer.A == self.B

    def is_same_as_mine(self, my_offer):
        return self.A == my_offer.A and self.B == my_offer.B

    @classmethod
    def from_data(cls, data):
        # TODO: verification
        x = cls(data["oid"], data["A"], data["B"])
        return x


class MyEOffer(EOffer):
    def __init__(self, oid, A, B, auto_post=True):
        super(MyEOffer, self).__init__(oid, A, B)
        self.auto_post = auto_post


class ETxSpec(object):
    def __init__(self, inputs, targets, my_utxo_list=None):
        self.inputs = inputs
        self.targets = targets
        self.my_utxo_list = my_utxo_list

    def get_data(self):
        return {"inputs": self.inputs,
                "targets": self.targets}

    @classmethod
    def from_data(cls, data):
        return cls(data['inputs'], data['targets'])


class EProposal(object):
    def __init__(self, pid, ewctrl, offer):
        self.pid = pid
        self.ewctrl = ewctrl
        self.offer = offer

    def get_data(self):
        return {"pid": self.pid,
                "offer": self.offer.get_data()}


class MyEProposal(EProposal):
    def __init__(self, ewctrl, orig_offer, my_offer):
        super(MyEProposal, self).__init__(make_random_id(),
                                          ewctrl, orig_offer)
        self.my_offer = my_offer
        if not orig_offer.matches(my_offer):
            raise Exception("offers are incongruent")
        self.etx_spec = ewctrl.make_etx_spec(self.offer.B, self.offer.A)
        self.etx_data = None

    def get_data(self):
        res = super(MyEProposal, self).get_data()
        if self.etx_data:
            res["etx_data"] = self.etx_data
        else:
            res["etx_spec"] = self.etx_spec.get_data()
        return res

    def process_reply(self, reply_ep):
        rtxs = RawTxSpec.from_tx_data(self.ewctrl.model,
                                      reply_ep.etx_data.decode('hex'))
        rtxs.sign(self.etx_spec.my_utxo_list)
        self.ewctrl.publish_tx(rtxs) # TODO: ???
        self.etx_data = rtxs.get_hex_tx_data()


class MyReplyEProposal(EProposal):
    def __init__(self, ewctrl, foreign_ep, my_offer):
        super(MyReplyEProposal, self).__init__(foreign_ep.pid,
                                             ewctrl,
                                             foreign_ep.offer)
        self.my_offer = my_offer
        self.tx = self.ewctrl.make_reply_tx(foreign_ep.etx_spec, 
                                            my_offer.A,
                                            my_offer.B)
        
    def get_data(self):
        data = super(MyReplyEProposal, self).get_data()
        data['etx_data'] = self.tx.get_hex_tx_data()
        return data

    def process_reply(self, reply_ep):
        rtxs = RawTxSpec.from_tx_data(self.ewctrl.model,
                                      reply_ep.etx_data.decode('hex'))
        self.ewctrl.publish_tx(rtxs) # TODO: ???
        

class ForeignEProposal(EProposal):
    def __init__(self, ewctrl, ep_data):
        offer = EOffer.from_data(ep_data['offer'])
        super(ForeignEProposal, self).__init__(ep_data['pid'], ewctrl, offer)
        self.etx_spec = None
        if 'etx_spec' in ep_data:
            self.etx_spec = ETxSpec.from_data(ep_data['etx_spec'])
        self.etx_data = ep_data.get('etx_data', None)

    def accept(self, my_offer):
        if not self.offer.is_same_as_mine(my_offer):
            raise Exception("incompatible offer")          # pragma: no cover
        if not self.etx_spec:
            raise Exception("need etx_spec")               # pragma: no cover
        return MyReplyEProposal(self.ewctrl, self, my_offer)
