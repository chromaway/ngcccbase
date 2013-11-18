import urllib2
import json
import time
import binascii

def make_random_id():
    import os
    bits = os.urandom(8)
    return binascii.hexlify(bits)

def LOGINFO(msg, *params):
    print msg % params


def LOGDEBUG(msg, *params):
    print msg % params


def LOGERROR(msg, *params):
    print msg % params


class HTTPExchangeComm:
    def __init__(self, config, url = 'http://localhost:8080/messages'):
        self.config = config
        self.agents = []
        self.lastpoll = -1
        self.url = url
        self.own_msgids = set()

    def add_agent(self, agent):
        self.agents.append(agent)

    def post_message(self, content):
        msgid = make_random_id()
        content['msgid'] = msgid
        self.own_msgids.add(msgid)
        LOGDEBUG( "----- POSTING MESSAGE ----")
        data = json.dumps(content)
        LOGDEBUG(data)
        u = urllib2.urlopen(self.url, data)
        return u.read() == 'Success'

    def poll_and_dispatch(self):
        url = self.url
        if self.lastpoll == -1:
            # TODO: this is deprecated
            url = url
        else:
            url = url + '?from_serial=%s' % (self.lastpoll+1)
        u = urllib2.urlopen(url)
        resp = json.loads(u.read())
        for x in resp:
            if int(x.get('serial',0)) > self.lastpoll: self.lastpoll = int(x.get('serial',0))
            content = x.get('content',None)
            if content and not content.get('msgid', '') in self.own_msgids:
                for a in self.agents:
                    a.dispatch_message(content)

    def update(self):
        # raises exception in case of a problem
        self.poll_and_dispatch()
        # agent state is not updated if poll raises exception
        for a in self.agents:
            a.update_state()
        return True

    def safe_update(self):
        try:
            self.update()
            return True
        except Exception as e:
            LOGERROR("Error in  HTTPExchangeComm.update: %s", e)
            return False
