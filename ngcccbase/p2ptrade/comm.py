import urllib2
import json
import time
import threading
import Queue

from utils import make_random_id, LOGINFO, LOGDEBUG, LOGERROR


class CommBase(object):
    def __init__(self):
        self.agents = []

    def add_agent(self, agent):
        self.agents.append(agent)


class HTTPComm(CommBase):
    def __init__(self, config, url = 'http://localhost:8080/messages'):
        super(HTTPComm, self).__init__()
        self.config = config
        self.lastpoll = -1
        self.url = url
        self.own_msgids = set()

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
            url = url + "?from_timestamp_rel=%s" % self.config['offer_expiry_interval']
        else:
            url = url + '?from_serial=%s' % (self.lastpoll+1)
        print (url)
        u = urllib2.urlopen(url)
        resp = json.loads(u.read())
        for x in resp:
            if int(x.get('serial',0)) > self.lastpoll: self.lastpoll = int(x.get('serial',0))
            content = x.get('content',None)
            if content and not content.get('msgid', '') in self.own_msgids:
                for a in self.agents:
                    a.dispatch_message(content)


class ThreadedComm(CommBase):
    class AgentProxy(object):
        def __init__(self, tc):
            self.tc = tc
        def dispatch_message(self, content):
            self.tc.receive_queue.put(content)

    def __init__(self, upstream_comm):
        super(ThreadedComm, self).__init__()
        self.upstream_comm = upstream_comm
        self.send_queue = Queue.Queue()
        self.receive_queue = Queue.Queue()
        self.comm_thread = CommThread(self, upstream_comm)
        upstream_comm.add_agent(self.AgentProxy(self))
    
    def post_message(self, content):
        self.send_queue.put(content)

    def poll_and_dispatch(self):
        while not self.receive_queue.empty():
            content = self.receive_queue.get()
            for a in self.agents:
                a.dispatch_message(content)

    def start(self):
        self.comm_thread.start()

    def stop(self):
        self.comm_thread.stop()
        self.comm_thread.join()


class CommThread(threading.Thread):
    def __init__(self, threaded_comm, upstream_comm):
        threading.Thread.__init__(self)
        self._stop = threading.Event()
        self.threaded_comm = threaded_comm
        self.upstream_comm = upstream_comm

    def run(self):
        send_queue = self.threaded_comm.send_queue
        receive_queue = self.threaded_comm.receive_queue
        while not self._stop.is_set():
            while not send_queue.empty():
                self.upstream_comm.post_message(send_queue.get())
            self.upstream_comm.poll_and_dispatch()
            time.sleep(1)

    def stop(self):
        self._stop.set()
