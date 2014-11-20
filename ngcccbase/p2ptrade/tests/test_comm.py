#!/usr/bin/env python

import time
import unittest
import json
from ngcccbase.p2ptrade.comm import CommBase, HTTPComm, ThreadedComm


MESSAGES = json.loads("""[{"content": {"A": {"color_spec": "obc:ca99e77717e7d79001d3b876272ab118133a69cc7cbd4bf89d523f1be5607095:0:277127", "value": 100}, "msgid": "2050de1a0bc6db0b", "B": {"color_spec": "", "value": 10000000}, "oid": "1fd1f7b6c9be0ae6"}, "timestamp": 1414688356, "serial": 100033, "id": "1fd1f7b6c9be0ae6"}, {"content": {"A": {"color_spec": "", "value": 4000000}, "msgid": "99e8245205e00778", "B": {"color_spec": "obc:ca99e77717e7d79001d3b876272ab118133a69cc7cbd4bf89d523f1be5607095:0:277127", "value": 40}, "oid": "dba9a94ec735428a"}, "timestamp": 1414688387, "serial": 100034, "id": "dba9a94ec735428a"}]""")


class MockHTTPInterface(object):

  def __init__(self):
    self.reset()

  def reset(self):
    self.poll_log = []
    self.poll_result = MESSAGES
    self.post_log = []
    self.post_returncode = True
    
  def poll(self, url):
    self.poll_log.append(url)
    return self.poll_result

  def post(self, url, data):
    self.post_log.append({'url':url, 'data':data})
    return self.post_returncode


class MockAgent(object):

  def __init__(self):
    self.reset()

  def reset(self):
    self.dispatch_log = []

  def dispatch_message(self, content):
    self.dispatch_log.append(content)


class TestBaseComm(unittest.TestCase):

  def test_add_agent(self):
    comm = CommBase()
    comm.add_agent("a")
    self.assertEqual(comm.agents, ["a"])
    comm.add_agent("b")
    self.assertEqual(comm.agents, ["a", "b"])


class TestHTTPComm(unittest.TestCase):

  def setUp(self):
    self.config = { 'offer_expiry_interval' : 1}
    self.url = 'http://localhost:8080/messages'
    self.comm = HTTPComm(self.config, self.url)
    self.http_interface = MockHTTPInterface()
    self.comm.http_interface = self.http_interface
    self.agent = MockAgent()
    self.comm.add_agent(self.agent)

  def test_post_message_content(self):
    self.http_interface.reset()
    content = {'test':"TEST"}
    self.comm.post_message(content)
    posted = self.http_interface.post_log[0]
    content['msgid'] = posted['data']['msgid']
    self.assertEqual(content, posted['data'])

  def test_post_message_saves_msgid(self):
    self.http_interface.reset()
    self.comm.post_message({})
    posted = self.http_interface.post_log[0]
    self.assertTrue(posted['data']['msgid'] in self.comm.own_msgids)

  def test_post_message_url(self):
    self.http_interface.reset()
    self.comm.post_message({})
    posted = self.http_interface.post_log[0]
    self.assertEqual(self.url, posted['url'])

  def test_post_message_sets_msgid(self):
    self.http_interface.reset()
    self.comm.post_message({})
    posted = self.http_interface.post_log[0]
    self.assertTrue('msgid' in posted['data'])

  def test_post_message_returncode(self):
    self.http_interface.reset()
    self.http_interface.post_returncode = False
    self.assertFalse(self.comm.post_message({}))
    self.http_interface.post_returncode = True
    self.assertTrue(self.comm.post_message({}))

  def test_poll_and_dispatch(self):
    self.http_interface.reset()
    self.comm.poll_and_dispatch()
    expected = [MESSAGES[0]["content"], MESSAGES[1]["content"]]
    self.assertEqual(self.agent.dispatch_log, expected)


class TestThreadedComm(unittest.TestCase):

  def setUp(self):
    self.config = { 'offer_expiry_interval' : 1}
    self.url = 'http://localhost:8080/messages'
    self.http_interface = MockHTTPInterface()
    self.agent = MockAgent()
    self.tcomm = ThreadedComm(self.config, self.url)
    self.tcomm.http_interface = self.http_interface
    self.tcomm.add_agent(self.agent)
    self.tcomm.start()
    time.sleep(self.tcomm.sleep_time * 2)

  def tearDown(self):
    time.sleep(self.tcomm.sleep_time * 2)
    self.tcomm.stop()

  def test_post_message(self):
    self.http_interface.reset()
    self.assertTrue(self.tcomm.post_message({}))
    time.sleep(self.tcomm.sleep_time * 2)
    self.assertEqual(len(self.http_interface.post_log), 1)

  def test_poll_and_dispatch(self):
    self.http_interface.reset()
    self.agent.reset()
    time.sleep(self.tcomm.sleep_time * 2)
    self.tcomm.poll_and_dispatch()
    self.assertTrue(len(self.http_interface.poll_log) > 0)
    self.assertTrue(len(self.agent.dispatch_log) > 0)
    self.assertNotEqual(self.tcomm.lastpoll, -1)

if __name__ == '__main__':
    unittest.main()




