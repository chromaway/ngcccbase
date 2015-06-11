from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint
from pycoin.encoding import (b2a_hashed_base58, from_bytes_32, to_bytes_32,
                             a2b_hashed_base58, public_pair_to_bitcoin_address,
                             public_pair_to_hash160_sec,
                             secret_exponent_to_wif)
from pycoin.key import validate


class InvalidAddressError(Exception):
    pass


def coloraddress_to_bitcoinaddress(coloraddress):
    if "@" not in coloraddress:
        return coloraddress  # already btcaddress
    colorid, btcaddress = coloraddress.split("@")
    return btcaddress


class AddressRecord(object):
    """Object that holds both address and color information
    Note this is now an Abstract Class.
    """
    def __init__(self, **kwargs):
        self.color_set = kwargs.get('color_set')
        self.testnet = kwargs.get('testnet')
        self.addressprefix = b'\x6f' if self.testnet else b"\0"
        self.wifprefix = b'\xef' if self.testnet else b"\x80"
        self.netcode = 'XTN' if self.testnet else 'BTC'

    def rawPubkey(self):
        return public_pair_to_hash160_sec(self.publicPoint.pair(), False)

    def get_color_set(self):
        """Access method for the color set associated
        with this address record
        """
        return self.color_set

    def __eq__(self, other):
        return self.get_data() == other.get_data()

    def __hash__(self):
        return 0

    def get_data(self):
        """Get this object as a JSON/Storage compatible dict.
        Useful for storage and persistence.
        """
        raw = self.wifprefix + to_bytes_32(self.rawPrivKey)
        return {"color_set": self.color_set.get_data(),
                "address_data": b2a_hashed_base58(raw)}

    def get_private_key(self):
        return secret_exponent_to_wif(self.rawPrivKey, False, self.wifprefix)

    def get_address(self):
        """Get the actual bitcoin address
        """
        return self.address

    def get_color_address(self):
        """This is the address that can be used for sending/receiving
        colored coins
        """
        if self.color_set.uncolored_only():
            return self.get_address()
        return "%s@%s" % (self.get_color_set().get_color_hash(),
                          self.get_address())


class LooseAddressRecord(AddressRecord):
    """Subclass of AddressRecord which is entirely imported.
    The address may be an existing one.
    """
    def __init__(self, **kwargs):
        """Create a LooseAddressRecord for a given wallet <model>,
        color <color_set> and address <address_data>. Also let the constructor
        know whether it's on <testnet> (optional).
        <address_data> is the privKey in base58 format
        """
        super(LooseAddressRecord, self).__init__(**kwargs)
        wif = kwargs['address_data']
        if not validate.is_wif_valid(wif, allowable_netcodes=[self.netcode]):
            raise InvalidAddressError
        bin_privkey = a2b_hashed_base58(wif)
        self.rawPrivKey = from_bytes_32(bin_privkey[1:])
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(
            self.publicPoint.pair(), compressed=False,
            address_prefix=self.addressprefix
        )

