# util.py
#
# Utility functions that don't belong anywhere else.


__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58encode(v):
    """Returns the b58 encoding of a string <v>.
    b58 encoding is the standard encoding for bitcoin addresses.
    """
    n = long(v.encode("hex"), 16)
    r = ""
    while n > 0:
        n, mod = divmod(n, 58)
        r = __b58chars[mod] + r

    pad = 0
    for c in v:
        if c == '\x00':
            pad += 1
        else:
            break

    return (__b58chars[0]*pad) + r


# ALL FUNCTIONS BELOW THIS LINE ARE CURRENTLY UNUSED

#Borrowed from pywallet and compacted
def b58decode(v, length):
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base**i)

    result = ''
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]:
            nPad += 1
        else:
            break

    result = chr(0)*nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def padToNearest16(data):
    from math import ceil
    s = len(data)
    data = num2ascii(s, 2) + data
    ns = len(data)
    data = data.ljust(int(ceil(float(ns) / 16.0)*16), ".")
    return data


def removeNearest16Pad(data):
    s = ascii2num(data[:2])
    data = data[2:][:s]
    return data


def num2ascii(n, size):
    return num2hex(n, size).decode("hex")


def ascii2num(a):
    return int(a.encode("hex"), 16)


def num2hex(n, size):
    return hex(n)[2:].zfill(size*2)


def satoshis2BTC(satoshis):
    return float(satoshis) / float(100000000)
