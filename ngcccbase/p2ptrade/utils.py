import os
import binascii
import urllib2
import json


def LOGINFO(msg, *params):
    print (msg % params)


def LOGDEBUG(msg, *params):
    print (msg % params)


def LOGERROR(msg, *params):
    print (msg % params)


def make_random_id():
    bits = os.urandom(8)
    return binascii.hexlify(bits)


class CommonEqualityMixin(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


class HTTPInterface(object): # TODO test it

  def poll(self, url):
    try:
      return json.loads(urllib2.urlopen(url).read())
    except ValueError:
      return [] # bad data
    except urllib2.URLError:
      return [] # connection issues

  def post(self, url, content):
    data = json.dumps(content)
    return urllib2.urlopen(url, data).read() == 'Success'

