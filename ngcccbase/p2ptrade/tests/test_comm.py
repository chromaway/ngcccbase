#!/usr/bin/env python

import SocketServer
import SimpleHTTPServer
import threading
import time
import unittest

from ngcccbase.p2ptrade.comm import HTTPComm, ThreadedComm, CommThread


class MockAgent(object):
    def dispatch_message(self, m):
        pass

class TestServer(threading.Thread):
    def __init__(self, address, port):
        super(TestServer, self).__init__()
        self.httpd = SocketServer.TCPServer((address, port), TestHandler)
    def run(self):
        self.httpd.serve_forever()
    def shutdown(self):
        self.httpd.shutdown()
        self.httpd.socket.close()


class TestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_response(self, response):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-length", len(response))
        self.end_headers()
        self.wfile.write(response)
        
    def do_POST(self):
        self.do_response("Success")

    def do_GET(self):
        self.do_response('[{"content": {"msgid":1, "a":"blah"}, "serial": 1}]')
        

class TestComm(unittest.TestCase):

    def setUp(self):
        self.config = {"offer_expiry_interval": 30, "ep_expiry_interval": 30}
        self.hcomm = HTTPComm(self.config)
        self.msg = {"msgid": 2, "a": "b"}
        self.httpd = TestServer("localhost", 8080)
        self.httpd.start()
        self.tcomm = ThreadedComm(self.hcomm)
        self.tcomm.add_agent(MockAgent())

    def tearDown(self):
        self.httpd.shutdown()

    def test_post_message(self):
        self.assertTrue(self.hcomm.post_message(self.msg))

    def test_poll_and_dispatch(self):
        self.hcomm.poll_and_dispatch()
        self.assertEqual(self.hcomm.lastpoll, 1)
        self.hcomm.poll_and_dispatch()
        self.assertEqual(self.hcomm.lastpoll, 1)

    def test_threadcomm(self):
        self.tcomm.start()
        time.sleep(2)
        self.hcomm.post_message(self.msg)
        self.tcomm.post_message(self.msg)
        self.tcomm.poll_and_dispatch()
        time.sleep(2)
        self.tcomm.stop()


if __name__ == '__main__':
    unittest.main()
