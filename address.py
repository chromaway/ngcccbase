#!/usr/bin/env python
"""
address.py

This file has the Address class, which is used for managing
addresses in the ngccc realm.
The main usage of this file is to create/retrieve addresses
from the bitcoin ecosystem.
"""

from ecdsa import SigningKey, SECP256k1
from pycoin.encoding import a2b_base58, b2a_hashed_base58, hash160, b2a_base58

import hashlib
import hmac


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

    def __init__(self, pubkey, privkey):
        """The address object consists of the public key and
        private key.
        """
        # validate that the keys correspond to the correct network
        if a2b_base58(pubkey)[0] == self.PUBLIC_KEY_PREFIX:
            self.pubkey = pubkey
            self.privkey = privkey
        else:
            raise InvalidAddressError("%s is not a public key for %s" %
                                      (pubkey, self.__class__.__name__))

    def rawPrivkey(self):
        """Returns the raw private key associated with this address.
        This is a raw 32-byte string with no checksums
        """
        # note the first byte determines what type of address
        #  and the last four are checksums
        return a2b_base58(self.privkey)[1:-4]

    def rawPubkey(self):
        """Returns the raw public key associated with this address.
        This is a raw 32-byte string with no checksums
        """
        # note the first byte determines what type of address
        #  and the last four are checksums
        return a2b_base58(self.pubkey)[1:-4]

    def ecdsaPrivkey(self):
        """Returns a SigningKey object for this address.
        Useful for being able to sign a transaction.
        """
        return SigningKey.from_string(
            string=self.rawPrivkey(), curve=SECP256k1)

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
        return cls.fromPrivkey(ecdsaPrivkey)

    @classmethod
    def fromPrivkey(cls, ecdsaPrivkey):
        """Returns a new Address object from the private key.
        The private key can be used to get the public key,
        hence the need only for the private key.
        """
        rawPrivkey = cls.PRIVATE_KEY_PREFIX + ecdsaPrivkey.to_string()
        privkey = b2a_hashed_base58(rawPrivkey)

        ecdsaPubkey = ecdsaPrivkey.get_verifying_key()
        rawPubkey = cls.PUBLIC_KEY_PREFIX + hash160(
            "\x04" + ecdsaPubkey.to_string())
        pubkey = b2a_hashed_base58(rawPubkey)

        return cls(pubkey, privkey)

    @classmethod
    def fromMasterKey(cls, master_key, color_string, index):
        """Returns a new Address object from several
        variables. Using a <master_key>, a <color_string>
        and an <index>, this method will generate an Address
        object that's deterministic.
        """
        h = hmac.new(
            str(master_key), "%s|%s" % (color_string, index), hashlib.sha256)

        # the seed string needs to be exactly 32 bytes long
        string = h.digest()
        return cls.new(string)

    @classmethod
    def fromObj(cls, data):
        """Returns an Address object from JSON <data>
        """
        pubkey = data["pubkey"]
        privkey = data["privkey"]

        return cls(pubkey, privkey)

    @classmethod
    def rawPubkeyToAddress(cls, raw):
        return b2a_hashed_base58(cls.PUBLIC_KEY_PREFIX + raw)

    def getJSONData(self):
        """Returns a dict that can later be plugged into
        the fromObj method for later retrieval of an Address.
        This is particularly useful for storing/retrieving
        from a data store."""
        return {"pubkey": self.pubkey, "privkey": self.privkey}


class TestnetAddress(Address):
    """TestnetAddress represents a Bitcoin Testnet address.
    Be sure that bitcoind is running with the "-testnet" flag.
    """
    PUBLIC_KEY_PREFIX = "\x6F"
    PRIVATE_KEY_PREFIX = "\xEF"


if __name__ == "__main__":
    # test the key generation
    test_key = 'a' * 32
    address = Address.new(test_key)
    print address.pubkey
    rawPubkey = Address.PUBLIC_KEY_PREFIX + hash160(
        "\x04" + address.rawPubkey())
    print b2a_hashed_base58(rawPubkey)
    assert address.privkey \
        == "5JZB2s2RCtRUunKiqMbb6rAj3Z7TkJwa8zknL1cfTFpWoQArd6n", \
        "address generation isn't what was expected"

    assert address.rawPrivkey() == test_key, "wrong priv key"
