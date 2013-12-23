import Queue
import time

from protocol_objects import MyEOffer, EOffer, MyEProposal, ForeignEProposal
from utils import LOGINFO, LOGDEBUG, LOGERROR


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
        self.offers_updated = False
        self.config = config
        self.event_handlers = {}
        comm.add_agent(self)

    def set_event_handler(self, event_type, handler):
        self.event_handlers[event_type] = handler

    def fire_event(self, event_type, data):
        eh = self.event_handlers.get(event_type)
        if eh:
            eh(data)

    def set_active_ep(self, ep):
        if ep is None:
            self.ep_timeout = None
            self.match_orders = True
        else:
            self.ep_timeout = time.time() + self.config['ep_expiry_interval']
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
                if self.active_ep and self.active_ep.my_offer.oid == my_offer.oid:
                    continue
                my_offer.refresh(self.config['offer_expiry_interval'])
                self.post_message(my_offer)

    def service_their_offers(self):
        for their_offer in self.their_offers.values():
            if their_offer.expired(-self.config.get('offer_grace_interval', 0)):
                del self.their_offers[their_offer.oid]
                self.fire_event('offers_updated', None)

    def _update_state(self):
        if not self.has_active_ep() and self.offers_updated:
            self.offers_updated = False
            self.match_offers()
        self.service_my_offers()
        self.service_their_offers()

    def register_my_offer(self, offer):
        assert isinstance(offer, MyEOffer)
        self.my_offers[offer.oid] = offer
        self.offers_updated = True
        self.fire_event('offers_updated', offer)
        self.fire_event('register_my_offer', offer)

    def cancel_my_offer(self, offer):
        if self.active_ep and (self.active_ep.offer.oid == offer.oid
                               or self.active_ep.my_offer.oid == offer.oid):
            self.set_active_ep(None)
        if offer.oid in self.my_offers:
            del self.my_offers[offer.oid]
        self.fire_event('offers_updated', offer)
        self.fire_event('cancel_my_offer', offer)

    def register_their_offer(self, offer):
        LOGINFO("register oid %s ", offer.oid)
        self.their_offers[offer.oid] = offer
        offer.refresh(self.config['offer_expiry_interval'])
        self.offers_updated = True
        self.fire_event('offers_updated', offer)

    def match_offers(self):
        if self.has_active_ep():
            return
        for my_offer in self.my_offers.values():
            for their_offer in self.their_offers.values():
                LOGINFO("matches %s", my_offer.matches(their_offer))
                if my_offer.matches(their_offer):
                    success = False
                    try:
                        self.make_exchange_proposal(their_offer, my_offer)
                        success = True
                    except Exception as e:                # pragma: no cover
                        LOGERROR("Exception during "      # pragma: no cover
                                 "matching offer %s", e)  # pragma: no cover
                        raise                             # pragma: no cover
                    if success:
                        return

    def make_exchange_proposal(self, orig_offer, my_offer):
        if self.has_active_ep():
            raise Exception("already have active EP (in makeExchangeProposal")
        ep = MyEProposal(self.ewctrl, orig_offer, my_offer)
        self.set_active_ep(ep)
        self.post_message(ep)
        self.fire_event('make_ep', ep)

    def dispatch_exchange_proposal(self, ep_data):
        ep = ForeignEProposal(self.ewctrl, ep_data)
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
        my_offer = self.my_offers[ep.offer.oid]
        reply_ep = ep.accept(my_offer)
        self.set_active_ep(reply_ep)
        self.post_message(reply_ep)
        self.fire_event('accept_ep', ep)

    def clear_orders(self, ep):
        self.fire_event('trade_complete', ep)
        try:
            if isinstance(ep, MyEProposal):
                if ep.my_offer:
                    del self.my_offers[ep.my_offer.oid]
                del self.their_offers[ep.offer.oid]
            else:
                del self.my_offers[ep.offer.oid]
        except Exception as e:                       # pragma: no cover
            LOGERROR("there was an exception "       # pragma: no cover
                     "when clearing offers: %s", e)  # pragma: no cover
        self.fire_event('offers_updated', None)

    def update_exchange_proposal(self, ep):
        LOGDEBUG("updateExchangeProposal")
        my_ep = self.active_ep
        assert my_ep and my_ep.pid == ep.pid
        my_ep.process_reply(ep)
        if isinstance(my_ep, MyEProposal):
            self.post_message(my_ep)
        # my_ep.broadcast()
        self.clear_orders(my_ep)
        self.set_active_ep(None)

    def post_message(self, obj):
        self.comm.post_message(obj.get_data())

    def dispatch_message(self, content):
        try:
            if 'oid' in content:
                o = EOffer.from_data(content)
                self.register_their_offer(o)
            elif 'pid' in content:
                self.dispatch_exchange_proposal(content)
        except Exception as e:                         # pragma: no cover
            LOGERROR("got exception %s "               # pragma: no cover
                     "when dispatching a message", e)  # pragma: no cover
            raise                                      # pragma: no cover

    def update(self):
        self.comm.poll_and_dispatch()
        self._update_state()
