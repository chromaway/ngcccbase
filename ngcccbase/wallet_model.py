"""
wallet_model.py

Wallet Model: part of Wallet MVC structure

Model provides facilities for working with addresses, coins and asset
definitions, but it doesn't implement high-level operations
(those are implemented in controller).
"""

import hmac
import hashlib
import json
import os

from collections import defaultdict
from pycoin.ecdsa import Point
from pycoin.ecdsa.secp256k1 import generator_secp256k1 as BasePoint
from pycoin.encoding import (b2a_base58, from_bytes_32,
                             hash160_sec_to_bitcoin_address,
                             public_pair_to_bitcoin_address)
from pycoin.wallet import Wallet

from coloredcoinlib import (ColorSet, BlockchainState, ColorDataBuilderManager,
                            FullScanColorDataBuilder, DataStoreConnection,
                            ColorDataStore, ColorMetaStore, ColorMap,
                            ThickColorData, toposorted)
from ngcccbase.services.electrum import EnhancedBlockchainState
from ngcccbase import txdb
from txcons import (BasicTxSpec, SimpleOperationalTxSpec,
                    TransactionSpecTransformer)
from utxodb import UTXOQuery, UTXOManager


class AssetDefinition(object):
    """Stores the definition of a particular asset, including its color set,
    it's name (moniker), and the wallet model that represents it.
    """
    def __init__(self, model, params):
        """Create an Asset for a given wallet <model> and configuration
        <params>. Note params has the color definitions used for this
        Asset.
        """
        self.model = model
        self.monikers = params.get('monikers', [])
        self.color_set = ColorSet(model.get_color_map(),
                                  params.get('color_set'))
        self.unit = int(params.get('unit', 1))

    def __repr__(self):
        return "%s: %s" % (self.monikers, self.color_set)

    def get_monikers(self):
        """Returns the list of monikers for this asset.
        """
        return self.monikers

    def get_color_set(self):
        """Returns the list of colors for this asset.
        """
        return self.color_set

    def get_colorvalue(self, utxo):
        """ return colorvalue for a given utxo"""
        if self.color_set.uncolored_only():
            return utxo.value
        else:
            if utxo.colorvalues:
                for cv in utxo.colorvalues:
                    if cv[0] in self.color_set.color_id_set:
                        return cv[1]
            raise Exception("cannot get colorvalue for UTXO: "
                            "no colorvalues available")

    def make_operational_tx_spec(self, tx_spec):
        """Given a <tx_spec> of type BasicTxSpec, return
        a SimpleOperationalTxSpec.
        """
        if (not isinstance(tx_spec, BasicTxSpec)
                or not tx_spec.is_monoasset() or not tx_spec.is_monocolor()):
            raise Exception('tx spec type not supported')
        op_tx_spec = SimpleOperationalTxSpec(self.model, self)
        color_id = list(self.color_set.color_id_set)[0]
        color_def = self.model.get_color_def(color_id)
        for target in tx_spec.targets:
            # TODO: translate colorvalues
            op_tx_spec.add_target(target[0], color_def, target[2])
        return op_tx_spec

    def parse_value(self, portion):
        """Returns actual number of Satoshis for this Asset
        given the <portion> of the asset.
        """
        return int(float(portion) * self.unit)

    def format_value(self, atoms):
        """Returns a string representation of the portion of the asset.
        can envolve rounding.  doesn't display insignificant zeros
        """
        return '{0:g}'.format(atoms / float(self.unit))

    def get_data(self):
        """Returns a JSON-compatible object that represents this Asset
        """
        return {
            "monikers": self.monikers,
            "color_set": self.color_set.get_data(),
            "unit": self.unit
            }


class AssetDefinitionManager(object):
    """Manager for asset definitions. Useful for interacting with
    various Assets.
    """
    def __init__(self, model, config):
        """Given a wallet <model> and a configuration <config>,
        create a new asset definition manager.
        """
        self.config = config
        self.model = model
        self.asset_definitions = []
        self.lookup_by_moniker = {}
        for ad_params in config.get('asset_definitions', []):
            self.register_asset_definition(AssetDefinition(model, ad_params))

        # add bitcoin as a definition
        if "bitcoin" not in self.lookup_by_moniker:
            btcdef = AssetDefinition(
                model, {
                    "monikers": ["bitcoin"],
                    "color_set": [""],
                    "unit": 100000000,
                    })
            self.lookup_by_moniker["bitcoin"] = btcdef
            self.asset_definitions.append(btcdef)
            self.update_config()

    def register_asset_definition(self, assdef):
        """Given an asset definition <assdef> in JSON-compatible format,
        register the asset with the manager. Note AssetDefinition's
        get_data can be used to get this definition for persistence.
        """
        self.asset_definitions.append(assdef)
        for moniker in assdef.get_monikers():
            if moniker in self.lookup_by_moniker:
                raise Exception(
                    'more than one asset definition have same moniker')
            self.lookup_by_moniker[moniker] = assdef

    def add_asset_definition(self, params):
        """Create a new asset with given <params>.
        params needs the following:
        monikers  - list of names (e.g. ["red", "blue"])
        color_set - list of color sets
                    (e.g. ["obc:f0bd5...a5:0:128649", "obc:a..0:0:147477"])
        """
        assdef = AssetDefinition(self.model, params)
        self.register_asset_definition(assdef)
        self.update_config()
        return assdef

    def get_asset_by_moniker(self, moniker):
        """Given a color name <moniker>, return the actual Asset Definition
        """
        return self.lookup_by_moniker.get(moniker)

    def update_config(self):
        """Write the current asset definitions to the persistent data-store
        """
        self.config['asset_definitions'] = \
            [assdef.get_data() for assdef in self.asset_definitions]

    def get_all_assets(self):
        """Returns a list of all assets managed by this manager.
        """
        return self.asset_definitions

    def get_asset_and_address(self, color_address):
        """Given a color address <color_address> return the asset
        and bitcoin address associated with the address. If the color
        described in the address isn't managed by this object,
        throw an exception.
        """

        if color_address.find('@') == -1:
            return (self.lookup_by_moniker.get('bitcoin'), color_address)

        color_set_hash, address = color_address.split('@')
        for asset in self.get_all_assets():
            if color_set_hash == asset.get_color_set().get_color_hash():
                return (asset, address)
        raise Exception("No asset has a color set with this hash: %s"
                        % color_set_hash)


class AddressRecord(object):
    """Object that holds both an Address AND Color.
    Note this is now an Abstract Class.
    """
    def __init__(self, **kwargs):
        pass

    def get_color_set(self):
        """Access method for the color set associated
        with this address record
        """
        return self.color_set

    def get_data(self):
        """Get this object as a JSON/Storage compatible dict.
        Useful for storage and persistence.
        """
        return {"color_set": self.color_set.get_data(),
                "address_data": b2a_base58(to_byte_32(self.rawPrivKey))}

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


class DeterministicAddressRecord(AddressRecord):
    """Subclass of AddressRecord which is entirely deterministic.
    DeterministicAddressRecord will use a single master key to
    create addresses for specific colors and bitcoin addresses.
    """
    def __init__(self, **kwargs):
        """Create an address for this color <color_set>
        and index <index> with the master key <master_key>.
        The address record returned for the same three variables
        will be the same every time, hence "deterministic".
        """
        self.color_set = kwargs.get('color_set')
        if len(self.color_set.get_data()) == 0:
            color_string = "genesis block"
        else:
            color_string = self.color_set.get_hash_string()

        self.testnet = kwargs.get('testnet')
        h = hmac.new(str(kwargs['master_key']),
                     "%s|%s" % (color_string, kwargs['index']), hashlib.sha256)
        string = h.digest()
        self.rawPrivKey = from_bytes_32(string)
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(self.publicPoint.pair(),
                                                      compressed=False,
                                                      is_test=self.testnet)


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
        pycoin_wallet = kwargs.get('pycoin_wallet')
        self.color_set = kwargs.get('color_set')
        color_string = hashlib.sha256(self.color_set.get_earliest()).digest()

        # use the hash of the color string to get the subkey we need
        while len(color_string):
            number = int(color_string[:4].encode('hex'), 16)
            pycoin_wallet = pycoin_wallet.subkey(i=number, is_prime=True,
                                                 as_private=True)
            color_string = color_string[4:]

        # now get the nth address in this wallet
        pycoin_wallet = pycoin_wallet.subkey(i=kwargs.get('index'),
                                             is_prime=True, as_private=True)

        self.testnet = kwargs.get('testnet')
        self.rawPrivKey = pycoin_wallet.secret_exponent
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(self.publicPoint.pair(),
                                                      compressed=False,
                                                      is_test=self.testnet)


class LooseAddressRecord(AddressRecord):
    """Subclass of AddressRecord which is entirely imported.
    The address may be an existing one.
    """
    def __init__(self, **kwargs):
        """Create a LooseAddressRecord for a given wallet <model>,
        color <color_set> and address <address_data>. Also let the constructor
        know whether it's on <testnet> (optional).
        <address_data> consists of:
        privKey
        pubKey
        """
        self.model = kwargs.get('model')
        self.color_set = ColorSet(self.model.get_color_map(),
                                  kwargs.get('color_set'))
        self.testnet = kwargs.get('testnet')
        self.rawPrivKey = from_bytes_32(
            a2b_hashed_base58(kwargs['address_data']))
        self.publicPoint = BasePoint * self.rawPrivKey
        self.address = public_pair_to_bitcoin_address(self.publicPoint.pair(),
                                                      compressed=False,
                                                      is_test=self.testnet)


class DWalletAddressManager(object):
    """This class manages the creation of new AddressRecords.
    Specifically, it keeps track of which colors have been created
    in this wallet and how many addresses of each color have been
    created in this wallet.
    """
    def __init__(self, model, config):
        """Create a deterministic wallet address manager given
        a wallet <model> and a configuration <config>.
        Note address manager configuration is in the key "dwam".
        """
        self.config = config
        self.testnet = config.get('testnet', False)
        self.model = model
        self.addresses = []

        # initialize the wallet manager if this is the first time
        #  this will generate a master key.
        params = config.get('dwam', None)
        if params is None:
            params = self.init_new_wallet()

        # master key is stored in a separate config entry
        self.master_key = config['dw_master_key']

        self.genesis_color_sets = params['genesis_color_sets']
        self.color_set_states = params['color_set_states']

        # import the genesis addresses
        for i, color_desc_list in enumerate(self.genesis_color_sets):
            addr = self.get_genesis_address(i)
            addr.color_set = ColorSet(self.model.get_color_map(),
                                      color_desc_list)
            self.addresses.append(addr)

        # now import the specific color addresses
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            color_set = ColorSet(self.model.get_color_map(), color_desc_list)
            params = {
                'testnet': self.testnet,
                'master_key': self.master_key,
                'color_set': color_set
                }
            for index in xrange(max_index + 1):
                params['index'] = index
                self.addresses.append(DeterministicAddressRecord(**params))

        # import the one-off addresses from the config
        for addr_params in config.get('addresses', []):
            addr_params['testnet'] = self.testnet
            addr_params['model'] = model
            try:
                address = LooseAddressRecord(**addr_params)
                self.addresses.append(address)
            except InvalidAddressError:
                address_type = "Testnet" if self.testnet else "Bitcoin"
                #print "%s is an invalid %s address" % (
                #    addr_params['address_data']['pubkey'], address_type)

    def init_new_wallet(self):
        """Initialize the configuration if this is the first time
        we're creating addresses in this wallet.
        Returns the "dwam" part of the configuration.
        """
        if not 'dw_master_key' in self.config:
            master_key = os.urandom(64).encode('hex')
            self.config['dw_master_key'] = master_key
        dwam_params = {
            'genesis_color_sets': [],
            'color_set_states': []
            }
        self.config['dwam'] = dwam_params
        return dwam_params

    def increment_max_index_for_color_set(self, color_set):
        """Given a color <color_set>, record that there is one more
        new address for that color.
        """
        # TODO: speed up, cache(?)
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            cur_color_set = ColorSet(self.model.get_color_map(),
                                     color_desc_list)
            if cur_color_set.equals(color_set):
                max_index += 1
                color_set_st['max_index'] = max_index
                return max_index
        self.color_set_states.append({"color_set": color_set.get_data(),
                                      "max_index": 0})
        return 0

    def get_new_address(self, asset_or_color_set):
        """Given an asset or color_set <asset_or_color_set>,
        Create a new DeterministicAddressRecord and return it.
        The DWalletAddressManager will keep that tally and
        persist it in storage, so the address will be available later.
        """
        if isinstance(asset_or_color_set, AssetDefinition):
            color_set = asset_or_color_set.get_color_set()
        else:
            color_set = asset_or_color_set
        index = self.increment_max_index_for_color_set(color_set)
        na = DeterministicAddressRecord(master_key=self.master_key,
                                        color_set=color_set, index=index,
                                        testnet=self.testnet)
        self.addresses.append(na)
        self.update_config()
        return na

    def get_genesis_address(self, genesis_index):
        """Given the index <genesis_index>, will return
        the Deterministic Address Record associated with that
        index. In general, that index corresponds to the nth
        color created by this wallet.
        """
        return DeterministicAddressRecord(
            master_key=self.master_key,
            color_set=ColorSet(self.model.get_color_map(), []),
            index=genesis_index, testnet=self.testnet)

    def get_new_genesis_address(self):
        """Create a new genesis address and return it.
        This will necessarily increment the number of genesis
        addresses from this wallet.
        """
        index = len(self.genesis_color_sets)
        self.genesis_color_sets.append([])
        self.update_config()
        address = self.get_genesis_address(index)
        address.index = index
        self.addresses.append(address)
        return address

    def update_genesis_address(self, address, color_set):
        """Updates the genesis address <address> to have a different
        color set <color_set>.
        """
        assert address.color_set.color_id_set == set([])
        address.color_set = color_set
        self.genesis_color_sets[address.index] = color_set.get_data()
        self.update_config()

    def get_some_address(self, color_set):
        """Returns an address associated with color <color_set>.
        This address will be essentially a random address in the
        wallet. No guarantees to what will come out.
        If there is not address corresponding to the color_set,
        thhis method will create one and return it.
        """
        acs = self.get_addresses_for_color_set(color_set)
        if acs:
            # reuse
            return acs[0]
        else:
            return self.get_new_address(color_set)

    def get_change_address(self, color_set):
        """Returns an address that can receive the change amount
        for a color <color_set>
        """
        return self.get_some_address(color_set)

    def get_all_addresses(self):
        """Returns the list of all AddressRecords in this wallet.
        """
        return self.addresses

    def get_addresses_for_color_set(self, color_set):
        """Given a color <color_set>, returns all AddressRecords
        that have that color.
        """
        return [addr for addr in self.addresses
                if color_set.intersects(addr.get_color_set())]

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
        self.config['dwam'] = dwam_params


class HDWalletAddressManager(DWalletAddressManager):
    """This class manages the creation of new AddressRecords.
    Specifically, it keeps track of which colors have been created
    in this wallet and how many addresses of each color have been
    created in this wallet. This is different from DWalletAddressManager
    in that it is BIP-0032 compliant.
    """
    def __init__(self, model, config):
        """Create a deterministic wallet address manager given
        a wallet <model> and a configuration <config>.
        Note address manager configuration is in the key "hdwam".
        """
        self.config = config
        self.testnet = config.get('testnet', False)
        self.model = model
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
            addr.color_set = ColorSet(self.model.get_color_map(),
                                      color_desc_list)
            self.addresses.append(addr)

        # now import the specific color addresses
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            color_set = ColorSet(self.model.get_color_map(), color_desc_list)
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
            addr_params['model'] = model
            try:
                address = LooseAddressRecord(**addr_params)
                self.addresses.append(address)
            except InvalidAddressError:
                address_type = "Testnet" if self.testnet else "Bitcoin"

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
            color_set=ColorSet(self.model.get_color_map(), []),
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


class ColoredCoinContext(object):
    """Interface to the Colored Coin Library's various offerings.
    Specifically, this object provides access to a storage mechanism
    (store_conn, cdstore, metastore), the color mapping (colormap)
    and color data (Thick Color Data)
    """
    def __init__(self, config):
        """Creates a Colored Coin Context given a config <config>
        """
        params = config.get('ccc', {})
        self.testnet = config.get('testnet', False)
        self.blockchain_state = BlockchainState.from_url(
            None, self.testnet)

        if not self.testnet:
            ok = False
            try:
                # try fetching transaction from the second block of
                # the bitcoin blockchain to see whether txindex works
                self.blockchain_state.bitcoind.getrawtransaction(
                    "9b0fc92260312ce44e74ef369f5c66bbb85848f2eddd5"
                    "a7a1cde251e54ccfdd5")
                ok = True
            except Exception as e:
                pass
            if not ok:
                # use Electrum to request transactions
                self.blockchain_state = EnhancedBlockchainState(
                    "electrum.cafebitcoin.com", 50001)

        self.store_conn = DataStoreConnection(
            params.get("colordb_path", "color.db"))
        self.cdstore = ColorDataStore(self.store_conn.conn)
        self.metastore = ColorMetaStore(self.store_conn.conn)

        self.colormap = ColorMap(self.metastore)

        cdbuilder = ColorDataBuilderManager(
            self.colormap, self.blockchain_state, self.cdstore,
            self.metastore, FullScanColorDataBuilder)

        self.colordata = ThickColorData(
            cdbuilder, self.blockchain_state, self.cdstore)

    def raw_to_address(self, raw_address):
        return hash160_sec_to_bitcoin_address(raw_address,
                                              is_test=self.testnet)


class CoinQueryFactory(object):
    """Object that creates Queries, which in turn query the UTXO store.
    """
    def __init__(self, model, config):
        """Given a wallet <model> and a config <config>,
        create a query factory.
        """
        self.model = model

    def make_query(self, query):
        """Create a UTXOQuery from query <query>. Queries are dicts with:
        color_set - color associated with this query
        """
        color_set = query.get('color_set')
        if not color_set:
            if 'color_id_set' in query:
                color_set = ColorSet.from_color_ids(
                    self.model.get_color_map(), query['color_id_set'])
            elif 'asset' in query:
                color_set = query['asset'].get_color_set()
            else:
                raise Exception('color set is not specified')
        return UTXOQuery(self.model, color_set)


class WalletModel(object):
    """Represents a colored-coin wallet
    """
    def __init__(self, config, store_conn):
        """Creates a new wallet given a configuration <config>
        """
        self.store_conn = store_conn  # hackish!
        self.ccc = ColoredCoinContext(config)
        self.ass_def_man = AssetDefinitionManager(self, config)
        if config.get('bip0032'):
            self.address_man = HDWalletAddressManager(self, config)
        else:
            self.address_man = DWalletAddressManager(self, config)

        self.coin_query_factory = CoinQueryFactory(self, config)
        self.utxo_man = UTXOManager(self, config)
        self.txdb = txdb.TxDb(self, config)
        self.testnet = config.get('testnet', False)
        self.tx_spec_transformer = TransactionSpecTransformer(self, config)

    def get_tx_db(self):
        """Access method for transaction data store.
        """
        return self.txdb

    def is_testnet(self):
        """Returns True if testnet mode is enabled.
        """
        return self.testnet

    def transform_tx_spec(self, tx_spec, target_spec_kind):
        """Pass-through for TransactionSpecTransformer's transform
        """
        return self.tx_spec_transformer.transform(tx_spec, target_spec_kind)

    def get_coin_query_factory(self):
        """Access Method for CoinQueryFactory
        """
        return self.coin_query_factory

    def make_coin_query(self, params):
        """Pass-through for CoinQueryFactory's make_query
        """
        return self.coin_query_factory.make_query(params)

    def get_asset_definition_manager(self):
        """Access Method for asset definition manager
        """
        return self.ass_def_man

    def get_address_manager(self):
        """Access method for address manager
        """
        return self.address_man

    def get_history_for_asset(self, asset):
        """Returns the history of how an address got its coins.
        """
        history = []
        address_lookup = {
            a.get_address(): 1 for a in
            self.address_man.get_addresses_for_color_set(
                asset.get_color_set())}

        for color in asset.color_set.color_id_set:
            colordef = self.get_color_def(color)
            color_transactions = self.ccc.cdstore.get_all(color)
            transaction_lookup = {}
            color_record = defaultdict(list)
            for row in color_transactions:
                txhash, outindex, colorvalue, other = row
                mempool = False
                if not transaction_lookup.get(txhash):
                    tx = self.ccc.blockchain_state.get_tx(txhash)
                    blockhash, x = self.ccc.blockchain_state.get_tx_blockhash(
                        txhash)
                    if blockhash:
                        height = self.ccc.blockchain_state.get_block_height(
                            blockhash)
                    else:
                        height = -1
                        mempool = True
                    transaction_lookup[txhash] = (tx, height)
                tx, height = transaction_lookup[txhash]
                output = tx.outputs[outindex]
                address = self.ccc.raw_to_address(output.raw_address)

                if address_lookup.get(address):
                    color_record[txhash].append({
                        'txhash': txhash,
                        'address': address,
                        'value': colorvalue,
                        'height': height,
                        'outindex': outindex,
                        'inindex': -1,
                        'mempool': mempool,
                        })

            # check the inputs
            seen_hashes = {}
            for txhash, tup in transaction_lookup.items():
                tx, height = tup
                mempool = height == -1
                for input_index, input in enumerate(tx.inputs):
                    inhash = input.prevout.hash
                    in_outindex = input.prevout.n
                    intx = self.ccc.blockchain_state.get_tx(inhash)
                    in_raw = intx.outputs[in_outindex]
                    address = self.ccc.raw_to_address(in_raw.raw_address)

                    # find the transaction that corresponds to this input
                    transaction = color_record.get(inhash)
                    if not transaction:
                        continue

                    # find the output transaction corresponding to this input
                    #  index and record it as being spent
                    for item in transaction:
                        if item['outindex'] == in_outindex:
                            color_record[txhash].append({
                                'txhash': txhash,
                                'address': address,
                                'value': -item['value'],
                                'height': height,
                                'inindex': input_index,
                                'outindex': -1,
                                'mempool': mempool,
                                })
                            break

            for txhash, color_record_transaction in color_record.items():
                for item in color_record_transaction:
                    value = item['value']
                    if value < 0:
                        item['action'] = 'sent'
                        item['value'] = -int(value)
                    elif txhash == colordef.genesis['txhash']:
                        item['action'] = 'issued'
                        item['value'] = int(value)
                    else:
                        item['action'] = 'received'
                        item['value'] = int(value)
                    history.append(item)

        def dependent_txs(txhash):
            """all transactions from current block this transaction
            directly depends on"""
            dependent_txhashes = []
            tx, height = transaction_lookup[txhash]
            for inp in tx.inputs:
                if inp.prevout.hash in transaction_lookup:
                    dependent_txhashes.append(inp.prevout.hash)
            return dependent_txhashes

        sorted_txhash_list = toposorted(transaction_lookup.keys(),
                                                 dependent_txs)
        txhash_position = {txhash:i for i, txhash
                           in enumerate(sorted_txhash_list)}

        def compare(a,b):
            """order in which we get back the history
            #1 - whether or not it's a mempool transaction
            #2 - height of the block the transaction is in
            #3 - whatever transaction is least dependent within a block
            #4 - whether we're sending or receiving
            #4 - outindex within a transaction/inindex within a transaction
            """
            return a['mempool'] - b['mempool'] \
                or a['height'] - b['height'] \
                or txhash_position[a['txhash']] - txhash_position[b['txhash']] \
                or a['outindex'] - b['outindex'] \
                or a['inindex'] - b['inindex']

        return sorted(history, cmp=compare)

    def get_color_map(self):
        """Access method for ColoredCoinContext's colormap
        """
        return self.ccc.colormap

    def get_color_def(self, color):
        return self.ccc.colormap.get_color_def(color)

    def get_utxo_manager(self):
        """Access method for Unspent Transaction Out manager.
        """
        return self.utxo_man
