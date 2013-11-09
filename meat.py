from ecdsa.curves import SECP256k1

import ecdsa
import hashlib
import json
import util

# Lambda's for hashes
sha256 = lambda h: hashlib.sha256(h).digest()
ripemd160 = lambda h: hashlib.new("ripemd160", h).digest()
md5 = lambda h: hashlib.md5(h).digest()


# exception for handling import of invalid addresses
class InvalidAddressError(Exception):
    pass


# Address class handles the actual address pairs,
# It creates them from using standard SECP256k1
# We should review the secp256k1 code and make sure it's right for security.
class Address:

    PUBLIC_KEY_PREFIX = "\x00"
    PRIVATE_KEY_PREFIX = "\x80"

    def __init__(self, pubkey, privkey, rawPubkey, rawPrivkey):
        # validate that the keys correspond to the correct network
        if rawPubkey[0] == self.PUBLIC_KEY_PREFIX:
            self.pubkey = pubkey
            self.privkey = privkey
            self.rawPrivkey = rawPrivkey
            self.rawPubkey = rawPubkey
        else:
            raise InvalidAddressError("%s is not a public key for %s" %
                                      (pubkey, self.__class__.__name__))

    # Creates new pair and returns address object
    @classmethod
    def new(cls, string=None):

        # Generates warner ECDSA objects
        if string:
            ecdsaPrivkey = ecdsa.SigningKey.from_string(
                string=string, curve=SECP256k1)
        else:
            ecdsaPrivkey = ecdsa.SigningKey.generate(
                curve=SECP256k1, entropy=None)
        ecdsaPrivkey = ecdsa.SigningKey.generate(curve=ecdsa.curves.SECP256k1)
        return cls.from_privkey(ecdsaPrivkey)

    @classmethod
    def from_privkey(cls, ecdsaPrivkey):
        ecdsaPubkey = ecdsaPrivkey.get_verifying_key()

        rawPrivkey = ecdsaPrivkey.to_string()
        rawPubkey = cls.PUBLIC_KEY_PREFIX + ripemd160(
            sha256("\x04" + ecdsaPubkey.to_string()))
        pubkeyChecksum = sha256(sha256(rawPubkey))[:4]
        rawPubkey += pubkeyChecksum

        pubkey = util.b58encode(rawPubkey)
        privkey = cls.PRIVATE_KEY_PREFIX + rawPrivkey
        privkeyChecksum = sha256(sha256(privkey))[:4]
        privkey = util.b58encode(privkey + privkeyChecksum)

        return cls(pubkey, privkey, rawPubkey, rawPrivkey)

    @classmethod
    def fromMasterKey(cls, master_key, color_string, index):
        base = "%s|%s|%s" % (master_key, color_string, index)
        # the seed string needs to be exactly 32, so use sha256
        string = hashlib.sha256(base).digest()
        return cls.new(string)

    # Creates pair from JSON parsed into standard python objects
    #  and returns address object
    @classmethod
    def fromObj(cls, data):
        pubkey = data["pubkey"]
        privkey = data["privkey"]
        rawPubkey = data["rawPubkey"].decode("hex")
        rawPrivkey = data["rawPrivkey"].decode("hex")

        return cls(pubkey, privkey, rawPubkey, rawPrivkey)

    # Returns JSON parsed into standard python objects and returns dictionary.
    #  This is for use with fromObj classmethod.
    def getJSONData(self):
        return {"pubkey": self.pubkey, "privkey": self.privkey,
                "rawPrivkey": self.rawPrivkey.encode("hex"),
                "rawPubkey": self.rawPubkey.encode("hex")}


class TestnetAddress(Address):

    PUBLIC_KEY_PREFIX = "\x6F"
    PRIVATE_KEY_PREFIX = "\xEF"
