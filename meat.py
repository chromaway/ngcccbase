# meat.py
#
# This file has the Address class, which is used for managing
#  addresses in the ngccc realm.
# The main usage of this file is to create/retrieve addresses
#  from the bitcoin ecosystem.

from ecdsa.curves import SECP256k1
from ecdsa import SigningKey
from util import b58encode

import hashlib
import hmac

# useful functions for hashing
sha256 = lambda h: hashlib.sha256(h).digest()
ripemd160 = lambda h: hashlib.new("ripemd160", h).digest()
md5 = lambda h: hashlib.md5(h).digest()

# useful constant for b58encode
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


class InvalidAddressError(Exception):
    """Exception represents an invalid address that was trying
    to be imported.
    """
    pass


class Address:
    """Address represents an actual bitcoin address.
    We create these addresses using the standard SECP256k1 curve
    from the ecdsa library. This is the standard cryptographical
    tool used for generating public/private keys. For more info
    on the curve, see: https://en.bitcoin.it/wiki/Secp256k1.

    Note that the Address is generic enough that by subclassing
    it, you can create testnet, litecoin or other types of addresses.
    """
    PUBLIC_KEY_PREFIX = "\x00"
    PRIVATE_KEY_PREFIX = "\x80"

    def __init__(self, pubkey, privkey, rawPubkey, rawPrivkey):
        """The address object consists of the public key and
        private key. rawPubkey and rawPrivkey are held in object
        for convenience. (for that matter, so is the public key)
        """
        # validate that the keys correspond to the correct network
        if rawPubkey[0] == self.PUBLIC_KEY_PREFIX:
            self.pubkey = pubkey
            self.privkey = privkey
            self.rawPrivkey = rawPrivkey
            self.rawPubkey = rawPubkey
        else:
            raise InvalidAddressError("%s is not a public key for %s" %
                                      (pubkey, self.__class__.__name__))

    @classmethod
    def new(cls, string=None):
        """Returns a new Address object.
        If a string is passed, the Address object will be
        created using that string and will be deterministic.
        If no string is passed, the Address object will
        be generated randomly.
        """
        # Generates warner ECDSA objects
        if string:
            # deterministic private key
            ecdsaPrivkey = SigningKey.from_string(
                string=string, curve=SECP256k1)
        else:
            # random private key
            ecdsaPrivkey = SigningKey.generate(
                curve=SECP256k1, entropy=None)
        return cls.from_privkey(ecdsaPrivkey)

    @classmethod
    def from_privkey(cls, ecdsaPrivkey):
        """Returns a new Address object from the private key.
        The private key can be used to get the public key,
        hence the need only for the private key.
        """
        ecdsaPubkey = ecdsaPrivkey.get_verifying_key()

        rawPrivkey = ecdsaPrivkey.to_string()
        rawPubkey = cls.PUBLIC_KEY_PREFIX + ripemd160(
            sha256("\x04" + ecdsaPubkey.to_string()))
        pubkeyChecksum = sha256(sha256(rawPubkey))[:4]
        rawPubkey += pubkeyChecksum

        pubkey = b58encode(rawPubkey)
        privkey = cls.PRIVATE_KEY_PREFIX + rawPrivkey
        privkeyChecksum = sha256(sha256(privkey))[:4]
        privkey = b58encode(privkey + privkeyChecksum)

        return cls(pubkey, privkey, rawPubkey, rawPrivkey)

    @classmethod
    def fromMasterKey(cls, master_key, color_string, index):
        """Returns a new Address object from several
        variables. Using a <master_key>, a <color_string>
        and an <index>, this method will generate an Address
        object that's deterministic.
        """
        h = hmac.new(master_key,
                     "%s|%s" % (color_string, index),
                     hashlib.sha256)
        # the seed string needs to be exactly 32 bytes long
        string = h.digest()
        return cls.new(string)

    @classmethod
    def fromObj(cls, data):
        """Returns an Address object from JSON <data>
        """
        pubkey = data["pubkey"]
        privkey = data["privkey"]
        rawPubkey = data["rawPubkey"].decode("hex")
        rawPrivkey = data["rawPrivkey"].decode("hex")

        return cls(pubkey, privkey, rawPubkey, rawPrivkey)

    def getJSONData(self):
        """Returns a dict that can later be plugged into
        the fromObj method for later retrieval of an Address.
        This is particularly useful for storing/retrieving
        from a data store."""
        return {"pubkey": self.pubkey, "privkey": self.privkey,
                "rawPrivkey": self.rawPrivkey.encode("hex"),
                "rawPubkey": self.rawPubkey.encode("hex")}


class TestnetAddress(Address):
    """TestnetAddress represents a Bitcoin Testnet address.
    Be sure that bitcoind is running with the "-testnet" flag.
    """
    PUBLIC_KEY_PREFIX = "\x6F"
    PRIVATE_KEY_PREFIX = "\xEF"
