"""
wallet_model.py

Wallet Model: part of Wallet MVC structure

Model provides facilities for working with addresses, coins and asset
definitions, but it doesn't implement high-level operations
(those are implemented in controller).
"""

from coloredcoinlib import blockchain, builder, store, colormap, colordata
from ngcccbase.services.electrum import EnhancedBlockchainState
from ngcccbase import txdb
from address import Address, TestnetAddress, InvalidAddressError

import hashlib
import json
import binascii

import txcons
import utxodb


def deterministic_json_dumps(obj):
    """TODO: make it even more deterministic!"""
    return json.dumps(obj, separators=(',', ':'), sort_keys=True)


class ColorSet(object):
    """A set of colors which belong to certain a asset.
    It can be used to filter addresses and UTXOs
    """
    def __init__(self, model, color_desc_list):
        """Creates a new color set given a wallet model <model>
        and color descriptions <color_desc_list>
        """
        self.color_desc_list = color_desc_list
        self.color_id_set = set()
        colormap = model.get_color_map()
        for color_desc in color_desc_list:
            self.color_id_set.add(colormap.resolve_color_desc(color_desc))

    def get_data(self):
        """Returns a list of strings that describe the colors.
        e.g. ["obc:f0bd5...a5:0:128649"]
        """
        return self.color_desc_list

    def get_hash_string(self):
        """Returns a deterministic string for this color set.
        Useful for creating deterministic addresses for a given color.
        """
        json = deterministic_json_dumps(
            sorted(self.color_desc_list))
        return hashlib.sha256(json).hexdigest()

    def has_color_id(self, color_id):
        """Returns boolean of whether color <color_id> is associated
        with this color set.
        """
        return (color_id in self.color_id_set)

    def intersects(self, other):
        """Given another color set <other>, returns whether
        they share a color in common.
        """
        return len(self.color_id_set & other.color_id_set) > 0

    def equals(self, other):
        """Given another color set <other>, returns whether
        they are the exact same color set.
        """
        return self.color_id_set == other.color_id_set

    @classmethod
    def from_color_ids(cls, model, color_ids):
        """Given a wallet model <model> and a list of colors <color_ids>
        return a ColorSet object.
        """
        colormap = model.get_color_map()
        color_desc_list = [colormap.find_color_desc(color_id)
                           for color_id in color_ids]
        return cls(model, color_desc_list)


class AssetDefinition(object):
    """Stores the definition of a particular asset, including its colour sets,
    it's name (moniker), and the wallet model that represents it.
    """
    def __init__(self, model, params):
        """Create an Asset for a given wallet <model> and configuration
        <params>. Note params has the color definitions used for this
        Asset.
        """
        self.model = model
        self.monikers = params.get('monikers', [])
        self.color_set = ColorSet(model, params.get('color_set'))
        self.unit = int(params.get('unit', 1))

    def get_monikers(self):
        """Returns the list of monikers for this asset.
        """
        return self.monikers

    def get_color_set(self):
        """Returns the list of colors for this asset.
        """
        return self.color_set

    def get_utxo_value(self, utxo):
        """ return asset value for a given utxo"""
        #  TODO: user colorvalues
        return utxo.value

    def make_operational_tx_spec(self, tx_spec):
        """Given a <tx_spec> of type BasicTxSpec, return
        a SimpleOperationalTxSpec.
        """
        if (not isinstance(tx_spec, txcons.BasicTxSpec)
                or not tx_spec.is_monoasset() or not tx_spec.is_monocolor()):
            raise Exception('tx spec type not supported')
        op_tx_spec = txcons.SimpleOperationalTxSpec(self.model, self)
        color_id = list(self.color_set.color_id_set)[0]
        for target in tx_spec.targets:
            # TODO: translate colorvalues
            op_tx_spec.add_target(target[0], color_id, target[2])
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
                "address_data": self.address.getJSONData()}

    def get_address(self):
        """Get the actual bitcoin address
        """
        return self.address.pubkey


class DeterministicAddressRecord(AddressRecord):
    """Subclass of AddressRecord which is entirely deterministic.
    DeterministicAddressRecord will use a single master key to
    create addresses for specific colors and bitcoin addresses.
    """
    def __init__(self, **kwargs):
        """Create an address for this wallet <model>, color
        <color_set> and index <index> with the master key <master_key>.
        The address record returned for the same four variables
        will be the same every time, hence "deterministic".
        """
        self.model = kwargs.get('model')
        self.color_set = kwargs.get('color_set')
        if len(self.color_set.get_data()) == 0:
            color_string = "genesis block"
        else:
            color_string = self.color_set.get_hash_string()
        cls = TestnetAddress if kwargs.get('testnet') else Address
        self.address = cls.fromMasterKey(
            kwargs['master_key'], color_string, kwargs['index'])


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
        self.color_set = ColorSet(self.model, kwargs.get('color_set'))
        cls = TestnetAddress if kwargs.get('testnet') else Address
        self.address = cls.fromObj(kwargs['address_data'])


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
            addr.color_set = ColorSet(self.model, color_desc_list)
            self.addresses.append(addr)

        # now import the specific color addresses
        for color_set_st in self.color_set_states:
            color_desc_list = color_set_st['color_set']
            max_index = color_set_st['max_index']
            color_set = ColorSet(self.model, color_desc_list)
            params = {
                'testnet': self.testnet,
                'master_key': self.master_key,
                'model': self.model,
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
            # privkey is in WIF format. not exactly
            # what we want, but passable, I guess
            master_key = Address.new().privkey
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
            cur_color_set = ColorSet(self.model, color_desc_list)
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
        na = DeterministicAddressRecord(
            model=self.model, master_key=self.master_key,
            color_set=color_set,
            index=index, testnet=self.testnet)
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
            model=self.model, master_key=self.master_key,
            color_set=ColorSet(self.model, []),
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

        if self.testnet:
            self.blockchain_state = blockchain.BlockchainState.from_url(
                None, self.testnet)
        else:
            self.blockchain_state = EnhancedBlockchainState(
                "btc.it-zone.org", 50001)

        self.store_conn = store.DataStoreConnection(
            params.get("color.db", "color.db"))
        self.cdstore = store.ColorDataStore(self.store_conn.conn)
        self.metastore = store.ColorMetaStore(self.store_conn.conn)

        self.colormap = colormap.ColorMap(self.metastore)

        cdbuilder = builder.ColorDataBuilderManager(
            self.colormap, self.blockchain_state, self.cdstore,
            self.metastore, builder.FullScanColorDataBuilder)

        self.colordata = colordata.ThickColorData(
            cdbuilder, self.blockchain_state, self.cdstore)


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
                color_set = ColorSet.from_color_ids(self.model,
                                                    query['color_id_set'])
            elif 'asset' in query:
                color_set = query['asset'].get_color_set()
            else:
                raise Exception('color set is not specified')
        return utxodb.UTXOQuery(self.model, color_set)


class WalletModel(object):
    """Represents a colored-coin wallet
    """
    def __init__(self, config, store_conn):
        """Creates a new wallet given a configuration <config>
        """
        self.store_conn = store_conn  # hackish!
        self.ccc = ColoredCoinContext(config)
        self.ass_def_man = AssetDefinitionManager(self, config)
        self.address_man = DWalletAddressManager(self, config)
        self.coin_query_factory = CoinQueryFactory(self, config)
        self.utxo_man = utxodb.UTXOManager(self, config)
        self.txdb = txdb.TxDb(self, config)
        self.testnet = config.get('testnet', False)
        self.tx_spec_transformer = txcons.TransactionSpecTransformer(
            self, config)

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
        klass = TestnetAddress if self.testnet else Address

        history = []

        address_lookup = {
            a.get_address(): 1 for a in
            self.address_man.get_addresses_for_color_set(
                asset.get_color_set())}

        for color in asset.color_set.color_id_set:
            colordef = self.ccc.colormap.get_color_def(
                color, self.ccc.blockchain_state)
            seen_hashes = {}
            for row in reversed(self.ccc.cdstore.get_all(color)):
                # address_ledger will keep track of the net
                #  affect on an address
                address_ledger = {}
                appended = 0
                txhash = row[0]
                if seen_hashes.get(txhash):
                    continue
                seen_hashes[txhash] = 1
                tx = self.ccc.blockchain_state.get_tx(txhash)
                for output in tx.outputs:
                    # find out where it went into
                    address = klass.rawPubkeyToAddress(output.raw_address)

                    if address_lookup.get(address):
                        address_ledger[address] = \
                            address_ledger.get(address, 0) + output.value

                for input in tx.inputs:
                    # find the hash referred to by the input
                    outpoint = input.outpoint
                    intx = self.ccc.blockchain_state.get_tx(outpoint.hash)
                    output = intx.outputs[outpoint.n]
                    address = klass.rawPubkeyToAddress(output.raw_address)
                    if address_lookup.get(address):
                        address_ledger[address] = \
                            address_ledger.get(address, 0) - output.value

                for address, value in address_ledger.items():
                    if value < 0:
                        history.append(["sent", -value, address])
                    elif txhash == colordef.genesis['txhash']:
                        history.append(["issued", value, address])
                    else:
                        history.append(["received", value, address])

                if len(address_ledger) == 0:
                    history.append(["unknown", txhash, ""])
        return history

    def get_color_map(self):
        """Access method for ColoredCoinContext's colormap
        """
        return self.ccc.colormap

    def get_utxo_manager(self):
        """Access method for Unspent Transaction Out manager.
        """
        return self.utxo_man
