import time
import binascii
from ngcccbase.txcons import RawTxSpec

def make_random_id():
    import os
    bits = os.urandom(8)
    return binascii.hexlify(bits)


class EOffer(object):
    # A = offerer's side, B = replyer's side
    # ie. offerer says "I want to give you A['value'] coins of color
    # A['colorid'] and receive B['value'] coins of color B['colorid']"
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
        def prop_matches(name):
            if (self.A[name] == offer.B[name]) \
                    and (self.B[name] == offer.A[name]):
                return True
        return prop_matches('value') and prop_matches('color_spec')

    def is_same_as_mine(self, my_offer):
        def checkprop(name):
            if self.A[name] != my_offer.A[name]:
                return False
            if self.B[name] != my_offer.B[name]:
                return False
            return True

        if not checkprop('color_spec'):
            return False
        if not checkprop('value'):
            return False
        return True

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
            raise Exception("incompatible offer")
        if not self.etx_spec:
            raise Exception("need etx_spec")
        return MyReplyEProposal(self.ewctrl, self, my_offer)
