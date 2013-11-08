# Wallet Model: part of Wallet MVC structure

# model provides facilities for working with addresses, coins and asset
#  definitions, but it doesn't implement high-level operations
#  (those are implemented in controller)

import meat
import txcons
import utxodb
import txdb
import hashlib


# A set of colors which belong to certain asset, it can be used to filter
#  addresses and UTXOs
class ColorSet(object):
    def __init__(self, model, color_desc_list):
        self.color_desc_list = color_desc_list
        self.color_id_set = set()
        colormap = model.get_color_map()
        for color_desc in color_desc_list:
            self.color_id_set.add(colormap.resolve_color_desc(color_desc))

    def get_data(self):
        return self.color_desc_list

    def to_string(self):
        # make this hex so we don't barf on string concatenation
        return hashlib.sha256(",".join(self.color_desc_list)).hexdigest()

    def has_color_id(self, color_id):
        return (color_id in self.color_id_set)

    def intersects(self, other):
        return len(self.color_id_set & other.color_id_set) > 0

    @classmethod
    def from_color_ids(cls, model, color_ids):
        colormap = model.get_color_map()
        color_desc_list = [colormap.find_color_desc(color_id)
                           for color_id in color_ids]
        return cls(model, color_desc_list)


# Stores the definition of a particular asset, including its colour sets,
#  it's name (moniker), and the wallet model that represents it.
class AssetDefinition(object):
    def __init__(self, model, params):
        self.model = model
        self.monikers = params.get('monikers', [])
        self.color_set = ColorSet(model, params.get('color_set'))
        self.max_index = params.get('max_index', 0)
        self.unit = int(params.get('unit', 1))

    def get_monikers(self):
        return self.monikers

    def get_color_set(self):
        return self.color_set

    def get_max_index(self):
        return self.max_index

    def get_utxo_value(self, utxo):
        return utxo.value

    def make_operational_tx_spec(self, tx_spec):
        if (not isinstance(tx_spec, txcons.BasicTxSpec)
                or not tx_spec.is_monoasset() or not tx_spec.is_monocolor()):
            raise Exception('tx spec type not supported')
        op_tx_spec = txcons.SimpleOperationalTxSpec(self.model, self)
        color_id = list(self.color_set.color_id_set)[0]
        for target in tx_spec.targets:
            # TODO: translate colorvalues
            op_tx_spec.add_target(target[0], color_id, target[2])
        return op_tx_spec

    def make_transaction_constructor(self):
        if self.color_set.color_id_set == set([0]):
            return txcons.UncoloredTC(self.model, self)
        else:
            if len(self.color_set.color_id_set) > 0:
                raise Exception('unable to make transaction constructor'
                                ' for more than one color')
            return txcons.MonocolorTC(self.model, self)

    # returns the atoms (truncate down)
    def parse_value(self, portion):
        return int(float(portion) * self.unit)

    # returns a string representation of the portion of the asset.
    # can envolve rounding.  doesn't display insignificant zeros
    def format_value(self, atoms):
        return '{0:g}'.format(atoms / float(self.unit))

    def get_data(self):
        return {
            "monikers": self.monikers,
            "color_set": self.color_set.get_data(),
            "max_index": self.max_index
            }


# Manages asset definitions
class AssetDefinitionManager(object):

    def __init__(self, model, config):
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
                    "max_index": 0,
                    })
            self.lookup_by_moniker["bitcoin"] = btcdef
            self.asset_definitions.append(btcdef)
            self.update_config()

    def register_asset_definition(self, assdef):
        self.asset_definitions.append(assdef)
        for moniker in assdef.get_monikers():
            if moniker in self.lookup_by_moniker:
                raise Exception(
                    'more than one asset definition have same moniker')
            color_set_key = assdef.get_color_set().to_string()
            self.lookup_by_moniker[moniker] = assdef

    def add_asset_definition(self, params):
        assdef = AssetDefinition(self.model, params)
        self.register_asset_definition(assdef)
        self.update_config()
        return assdef

    def get_asset_by_moniker(self, moniker):
        return self.lookup_by_moniker.get(moniker)

    def update_config(self):
        self.config['asset_definitions'] = \
            [assdef.get_data() for assdef in self.asset_definitions]

    def get_all_assets(self):
        return self.asset_definitions


class AddressRecord(object):
    """data associated with an address: keypair, color_set, ..."""
    def __init__(self, **kwargs):
        pass

    def get_color_set(self):
        return self.color_set

    def get_data(self):
        return {"color_set": self.color_set.get_data(),
                "address_data": self.meat.getJSONData()}

    def get_address(self):
        return self.meat.pubkey


class DeterministicAddressRecord(AddressRecord):
    """All addresses that are determined by the master key"""
    def __init__(self, **kwargs):
        self.model = kwargs.get('model')
        self.color_set = kwargs.get('color_set')
        if len(self.color_set.get_data()) == 0:
            color_string = "genesis block"
        else:
            color_string = self.color_set.to_string()
        cls = meat.TestnetAddress if kwargs.get('testnet') else meat.Address
        self.meat = cls.fromMasterKey(
            kwargs['master_key'], color_string, kwargs['index'])


class LooseAddressRecord(AddressRecord):
    """All addresses imported manually from the config"""
    def __init__(self, **kwargs):
        self.model = kwargs.get('model')
        self.color_set = kwargs.get('color_set')
        cls = meat.TestnetAddress if kwargs.get('testnet') else meat.Address
        self.meat = cls.fromObj(kwargs)


class WalletAddressManager(object):
    def __init__(self, model, adm, config):
        self.config = config
        self.testnet = config.get('testnet', False)
        self.model = model
        self.master_key = config.get('master_key', None)
        self.addresses = []
        self.adm = adm
        self.genesis_color_sets = config.get('genesis_color_sets')
        self.max_genesis_index = len(self.genesis_color_sets)

        # import the genesis addresses
        for i, color_set in enumerate(self.genesis_color_sets):
            addr = self.get_genesis_address(i)
            addr.color_set = ColorSet(self.model, color_set)
            self.addresses.append(addr)

        # now import the specific color addresses
        for asset in adm.get_all_assets():
            params = {
                'testnet': self.testnet,
                'master_key': self.master_key,
                'model': self.model,
                'color_set': asset.get_color_set()
                }
            for index in range(asset.get_max_index()):
                params['index'] = index
                self.addresses.append(DeterministicAddressRecord(**params))

        # import the one-off addresses from the config
        for addr_params in config.get('addresses', []):
            addr_params['testnet'] = self.testnet
            try:
                address = LooseAddressRecord(model, **addr_params)
                self.addresses.append(address)
            except meat.InvalidAddressError:
                address_type = "Testnet" if self.testnet else "Bitcoin"
                #print "%s is an invalid %s address" % (addr_params['address_data']['pubkey'], address_type)

    def get_new_address(self, asset):
        na = DeterministicAddressRecord(
            model=self.model, master_key=self.master_key,
            color_set=asset.get_color_set(),
            index=asset.max_index, testnet=self.testnet)
        asset.max_index += 1
        self.adm.update_config()
        self.addresses.append(na)
        self.update_config()
        return na

    def get_genesis_address(self, genesis_index):
        return DeterministicAddressRecord(
            model=self.model, master_key=self.master_key,
            color_set=ColorSet(self.model, []),
            index=genesis_index, testnet=self.testnet)

    def add_genesis_color_set(self, color_set):
        self.genesis_color_sets.append(color_set)

    def get_change_address(self, color_set):
        acs = self.get_addresses_for_color_set(color_set)
        if acs:
            # reuse
            return acs[0]
        else:
            return self.get_new_addres(color_set)

    def get_all_addresses(self):
        return self.addresses

    def get_addresses_for_color_set(self, color_set):
        return [addr for addr in self.addresses
                if color_set.intersects(addr.get_color_set())]

    def update_config(self):
        self.config['genesis_color_sets'] = self.genesis_color_sets


class ColoredCoinContext(object):
    def __init__(self, config):

        params = config.get('ccc', {})
        self.testnet = config.get('testnet', False)

        from coloredcoinlib import blockchain
        from coloredcoinlib import builder
        from coloredcoinlib import store
        from coloredcoinlib import colormap
        from coloredcoinlib import colordata
        from electrum import EnhancedBlockchainState

        if self.testnet:
            self.blockchain_state = blockchain.BlockchainState(
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
    def __init__(self, model, config):
        self.model = model

    def make_query(self, query):
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
    def __init__(self, config):
        self.ccc = ColoredCoinContext(config)
        self.ass_def_man = AssetDefinitionManager(self, config)
        self.address_man = WalletAddressManager(self, self.ass_def_man, config)
        self.coin_query_factory = CoinQueryFactory(self, config)
        self.utxo_man = utxodb.UTXOManager(self, config)
        self.txdb = txdb.TxDb(self, config)
        self.tx_spec_transformer = txcons.TransactionSpecTransformer(
            self, config)

    def get_tx_db(self):
        return self.txdb

    def transform_tx_spec(self, tx_spec, target_spec_kind):
        return self.tx_spec_transformer.transform(tx_spec, target_spec_kind)

    def get_coin_query_factory(self):
        return self.coin_query_factory

    def make_coin_query(self, params):
        return self.coin_query_factory.make_query(params)

    def get_asset_definition_manager(self):
        return self.ass_def_man

    def get_address_manager(self):
        return self.address_man

    def get_color_map(self):
        return self.ccc.colormap

    def get_utxo_manager(self):
        return self.utxo_man
