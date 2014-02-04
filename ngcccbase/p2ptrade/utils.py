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
