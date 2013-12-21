import hashlib
import os

from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint
from pycoin.encoding import public_pair_to_bitcoin_address
from pycoin.wallet import Wallet

from address import AddressRecord, LooseAddressRecord
from asset import AssetDefinition
from coloredcoinlib import ColorSet
from deterministic import DWalletAddressManager


class BIP0032AddressRecord(AddressRecord):
    """Subclass of AddressRecord which is deterministic and BIP0032 compliant.
    BIP0032AddressRecord will use a pycoin wallet to create addresses
    for specific colors.
    """
    def __init__(self, **kwargs):
        """Create an address for this color <color_set> and index <index>
        with the pycoin_wallet <pycoin_wallet> and on testnet or not
        <testnet>
        The address record returned for the same variables
        will be the same every time, hence "deterministic".
        """
        super(BIP0032AddressRecord, self).__init__(**kwargs)

        pycoin_wallet = kwargs.get('pycoin_wallet')
        color_string = hashlib.sha256(self.color_set.get_earliest()).digest()

        self.index = kwargs.get('index')

        # use the hash of the color string to get the subkey we need
        while len(color_string):
            number = int(color_string[:4].encode('hex'), 16)
            pycoin_wallet = pycoin_wallet.subkey(i=number, is_prime=True,
                                                 as_private=True)
            color_string = color_string[4:]

        # now get the nth address in this wallet
        pycoin_wallet = pycoin_wallet.subkey(i=self.index,
                                             is_prime=True, as_private=True)

        self.rawPrivKey = pycoin_wallet.secret_exponent
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(self.publicPoint.pair(),
                                                      compressed=False,
                                                      is_test=self.testnet)


class HDWalletAddressManager(DWalletAddressManager):
    """This class manages the creation of new AddressRecords.
    Specifically, it keeps track of which colors have been created
    in this wallet and how many addresses of each color have been
    created in this wallet. This is different from DWalletAddressManager
    in that it is BIP-0032 compliant.
    """
    def __init__(self, colormap, config):
        """Create a deterministic wallet address manager given
        a color map <colormap> and a configuration <config>.
        Note address manager configuration is in the key "hdwam".
        """
        self.config = config
        self.testnet = config.get('testnet', False)
        self.colormap = colormap
        self.addresses = []

        # initialize the wallet manager if this is the first time
        #  this will generate a master key.
        params = config.get('hdwam', None)
        if params is None:
            params = self.init_new_wallet()

        # master key is stored in a separate config entry
        self.master_key = config['hdw_master_key']

        master = hashlib.sha512(self.master_key.decode('hex')).digest()

        # initialize a BIP-0032 wallet
        self.pycoin_wallet = Wallet(is_private=True, is_test=self.testnet,
                                    chain_code=master[32:],
                                    secret_exponent_bytes=master[:32])

        self.genesis_color_sets = params['genesis_color_sets']
        self.color_set_states = params['color_set_states']

        # import the genesis addresses
        for i, color_desc_list in enumerate(self.genesis_color_sets):
            addr = self.get_genesis_address(i)
            addr.color_set = ColorSet(self.colormap,
                                      color_desc_list)
            self.addresses.append(addr)

        # now import the specific color addresses
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            color_set = ColorSet(self.colormap, color_desc_list)
            params = {
                'testnet': self.testnet,
                'pycoin_wallet': self.pycoin_wallet,
                'color_set': color_set
                }
            for index in xrange(max_index + 1):
                params['index'] = index
                self.addresses.append(BIP0032AddressRecord(**params))

        # import the one-off addresses from the config
        for addr_params in config.get('addresses', []):
            addr_params['testnet'] = self.testnet
            addr_params['color_set'] = ColorSet(self.colormap,
                                                addr_params['color_set'])
            address = LooseAddressRecord(**addr_params)
            self.addresses.append(address)

    def init_new_wallet(self):
        """Initialize the configuration if this is the first time
        we're creating addresses in this wallet.
        Returns the "hdwam" part of the configuration.
        """
        if not 'hdw_master_key' in self.config:
            master_key = os.urandom(64).encode('hex')
            self.config['hdw_master_key'] = master_key
        hdwam_params = {
            'genesis_color_sets': [],
            'color_set_states': []
            }
        self.config['hdwam'] = hdwam_params
        return hdwam_params

    def get_new_address(self, asset_or_color_set):
        """Given an asset or color_set <asset_or_color_set>,
        Create a new BIP0032AddressRecord and return it.
        This class will keep that tally and
        persist it in storage, so the address will be available later.
        """
        if isinstance(asset_or_color_set, AssetDefinition):
            color_set = asset_or_color_set.get_color_set()
        else:
            color_set = asset_or_color_set
        index = self.increment_max_index_for_color_set(color_set)
        na = BIP0032AddressRecord(
            pycoin_wallet=self.pycoin_wallet, color_set=color_set,
            index=index, testnet=self.testnet)
        self.addresses.append(na)
        self.update_config()
        return na

    def get_genesis_address(self, genesis_index):
        """Given the index <genesis_index>, will return
        the BIP0032 Address Record associated with that
        index. In general, that index corresponds to the nth
        color created by this wallet.
        """
        return BIP0032AddressRecord(
            pycoin_wallet=self.pycoin_wallet,
            color_set=ColorSet(self.colormap, []),
            index=genesis_index, testnet=self.testnet)

    def update_config(self):
        """Updates the configuration for the address manager.
        The data will persist in the key "dwam" and consists
        of this data:
        genesis_color_sets - Colors created by this wallet
        color_set_states   - How many addresses of each color
        """
        dwam_params = {
            'genesis_color_sets': self.genesis_color_sets,
            'color_set_states': self.color_set_states
            }
        self.config['hdwam'] = dwam_params
