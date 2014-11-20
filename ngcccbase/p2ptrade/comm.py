import time
import threading
import Queue

from utils import make_random_id, HTTPInterface


class CommBase(object):

  def __init__(self):
    self.agents = []

  def add_agent(self, agent):
    self.agents.append(agent)

  def poll_and_dispatch(self):
    self.dispatch(self.poll())

  def dispatch(self, messages):
    for message in messages:
      for agent in self.agents:
        agent.dispatch_message(message)

  def post_message(self, content):
    raise Exception("Called abstract method!")

  def poll(self):
    raise Exception("Called abstract method!")


class HTTPComm(CommBase):

  def __init__(self, config, url):
    super(HTTPComm, self).__init__()
    self.config = config
    self.lastpoll = -1
    self.url = url
    self.own_msgids = set()
    self.http_interface = HTTPInterface()

  def post_message(self, content):
    msgid = make_random_id()
    content['msgid'] = msgid
    self.own_msgids.add(msgid)
    return self.http_interface.post(self.url, content)
  
  def poll(self):
    messages = []
    url = self.url
    if self.lastpoll == -1:
      interval = self.config['offer_expiry_interval']
      url = url + "?from_timestamp_rel=%s" % interval
    else:
      url = url + '?from_serial=%s' % (self.lastpoll+1)
    for envelope in self.http_interface.poll(url):
      if int(envelope.get('serial',0)) > self.lastpoll: 
        self.lastpoll = int(envelope.get('serial',0))
      content = envelope.get('content',None)
      if content and content.get('msgid', '') not in self.own_msgids:
        messages.append(content)
    return messages


class ThreadedComm(HTTPComm):

  def __init__(self, *args, **kwargs):
    super(ThreadedComm, self).__init__(*args, **kwargs)
    self.sleep_time = 1
    self.send_queue = Queue.Queue()
    self.receive_queue = Queue.Queue()
    self.thread = self._Thread(self)
  
  def post_message(self, content):
    self.send_queue.put(content)
    return True

  def poll(self):
    messages = []
    receive_queue = self.receive_queue
    while not receive_queue.empty():
      messages.append(receive_queue.get())
    return messages

  def start(self):
    self.thread.start()

  def stop(self):
    self.thread.stop()
    self.thread.join()

  class _Thread(threading.Thread):

    def __init__(self, threaded_comm):
      threading.Thread.__init__(self)
      self._stop = threading.Event()
      self.threaded_comm = threaded_comm

    def run(self):
      send_queue = self.threaded_comm.send_queue
      receive_queue = self.threaded_comm.receive_queue
      while not self._stop.is_set():

        # async send messages
        while not send_queue.empty():
          super(ThreadedComm, self.threaded_comm).post_message(send_queue.get())

        # async poll messages
        for message in super(ThreadedComm, self.threaded_comm).poll():
          receive_queue.put(message)

        # wait
        time.sleep(self.threaded_comm.sleep_time)

    def stop(self):
      self._stop.set()

