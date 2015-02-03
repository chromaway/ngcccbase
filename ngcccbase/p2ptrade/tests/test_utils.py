#!/usr/bin/env python

import re
import unittest
from ngcccbase.p2ptrade.utils import make_random_id


class TestMakeRandomId(unittest.TestCase):

  def test_is_random(self):
    self.assertTrue(make_random_id() != make_random_id())

  def test_at_least_8_bytes_of_entropy(self):
    self.assertTrue(len(make_random_id()) >= 16)

  def test_is_hex_str(self):
    is_hex = lambda x: bool(re.match("[0123456789abcdef]*", x))
    self.assertTrue(is_hex(make_random_id()))


class TestHTTPInterface(unittest.TestCase):

  def test_poll(self):
    pass # TODO test it

  def test_post(self):
    pass # TODO test it


if __name__ == '__main__':
    unittest.main()

