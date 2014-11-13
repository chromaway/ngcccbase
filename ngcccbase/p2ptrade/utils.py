import os
import binascii


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
