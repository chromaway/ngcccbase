import time


def LOGINFO(msg):
    pass


def LOGDEBUG(msg):
    pass


def LOGERROR(msg):
    pass


class EAgent(object):
    """implements high-level exchange logic, keeps track of the state
       (offers, propsals)"""

    def __init__(self, ewctrl, config, comm):
        self.ewctrl = ewctrl
        self.my_offers = dict()
        self.their_offers = dict()
        self.active_ep = None
        self.ep_timeout = None
        self.comm = comm
        self.match_offers = False
        self.config = config

    def set_active_ep(self, ep):
        if ep is None:
            self.ep_timeout = None
            self.match_orders = True
        else:
            self.ep_timeout = time.time() + self.config.ep_expiry_interval
        self.active_ep = ep

    def has_active_ep(self):
        if self.ep_timeout and self.ep_timeout < time.time():
            self.set_active_ep(None)  # TODO: cleanup?
        return self.active_ep is not None

    def service_my_offers(self):
        for my_offer in self.my_offers.values():
            if my_offer.auto_post:
                if not my_offer.expired():
                    continue
                if self.active_ep and self.active_ep.offer.oid == my_offer.oid:
                    continue
                my_offer.refresh(self.config.offer_expiry_interval)
                self.postMessage(my_offer)

    def service_their_offers(self):
        for their_offer in self.their_offers.values():
            if their_offer.expired(-standard_offer_grace_interval):
                del self.their_offers[their_offer.oid]

    def update_state(self):
        if not self.has_active_ep() and self.match_offers:
            self.match_offers = False
            self.match_offers()
        self.service_my_offers()
        self.service_their_offers()

    def register_my_offer(self, offer):
        assert isinstance(offer, MyEOffer)
        self.my_offers[offer.oid] = offer
        self.match_offers = True

    def cancel_my_offer(self, offer):
        if self.active_ep and (self.active_ep.offer.oid == offer.oid
                               or self.active_ep.my_offer.oid == offer.oid):
            self.set_active_ep(None)
        if offer.oid in self.my_offers:
            del self.my_offers[offer.oid]

    def register_their_offer(self, offer):
        LOGINFO("register oid %s ", offer.oid)
        self.their_offers[offer.oid] = offer
        offer.refresh()
        self.match_offers = True

    def match_offers(self):
        if self.has_active_ep():
            return
        for my_offer in self.my_offers.values():
            for their_offer in self.their_offers.values():
                if my_offer.matches(their_offer):
                    success = False
                    try:
                        self.make_exchange_proposal(their_offer, my_offer)
                        success = True
                    except Exception as e:
                        LOGERROR("Exception during matching offer %s", e)
                    if success:
                        return

    def make_exchange_proposal(self, orig_offer, my_offer):
        if self.has_active_ep():
            raise Exception("already have active EP (in makeExchangeProposal")
        ep = MyEProposal(self.ewctrl, orig_offer, my_offer)
        self.set_active_ep(ep)
        self.post_message(ep)

    def dispatch_exchange_proposal(self, ep_data):
        ep = ForeignEProposal(ep_data)
        LOGINFO("ep oid:%s, pid:%s, ag:%s", ep.offer.oid, ep.pid, self)
        if self.has_active_ep():
            LOGDEBUG("has active EP")
            if ep.pid == self.active_ep.pid:
                return self.update_exchange_proposal(ep)
        else:
            if ep.offer.oid in self.my_offers:
                LOGDEBUG("accept exchange proposal")
                return self.accept_exchange_proposal(ep)
        # We have neither an offer nor a proposal matching
        #  this ExchangeProposal
        if ep.offer.oid in self.their_offers:
            # remove offer if it is in-work
            # TODO: set flag instead of deleting it
            del self.their_offers[ep.offer.oid]
        return None

    def accept_exchange_proposal(self, ep):
        if self.has_active_ep():
            return
        their_offer = ep.offer
        my_offer = self.my_offers[offer.oid]
        if ep.is_valid(my_offer):
            reply_ep = ep.make_reply()
            self.set_active_ep(reply_ep)
            self.post_message(ep)
        else:
            raise Exception("ep isn't valid")

    def clear_orders(self, ep):
        try:
            if isinstance(ep, MyEProposal):
                if ep.my_offer:
                    del self.my_offers[ep.my_offer.oid]
                del self.their_offers[ep.offer.oid]
            else:
                del self.my_offers[ep.offer.oid]
        except Exception as e:
            LOGERROR("there was an exception when clearing offers: %s", e)

    def update_exchange_proposal(self, ep):
        LOGDEBUG("updateExchangeProposal")
        my_ep = self.active_ep
        assert my_ep and my_ep.pid == ep.pid
        offer = my_ep.offer

        if isinstance(my_ep, MyEProposal):
            my_ep.validate_and_sign(ep)
        else:
            # TODO: process reply
            return
        my_ep.broadcast()
        self.clear_orders(my_ep)
        self.set_active_ep(None)

    def post_message(self, obj):
        self.comm.post_message(obj.get_data())

    def dispatch_message(self, content):
        pass
        #try:
        #    if 'oid' in content:
        #        o = ExchangeOffer.importTheirs(content)
        #        self.registerTheirOffer(o)
        #    elif 'pid' in content:
        #        self.dispatchExchangeProposal(content)
        #except Exception as e:
        #    LOGERROR("got exception %s when dispatching a message", e)
