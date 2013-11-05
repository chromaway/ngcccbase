# Wallet Model: part of Wallet MVC structure

# model provides facilities for working with addresses, coins and asset definitions,
# but it doesn't implement high-level operations (those are implemented in controller)

import meat
import txcons
import utxodb
from ngcccbase import txdb

# A set of colors which belong to certain asset, it can be used to filter addresses and UTXOs
class ColorSet(object):
    def __init__(self, model, color_desc_list):
        self.color_desc_list = color_desc_list
        self.color_id_set = set()
        colormap = model.get_color_map()
        for color_desc in color_desc_list:
            self.color_id_set.add(colormap.resolve_color_desc(color_desc))

    def get_data(self):
        return self.color_desc_list

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

# Stores the definition of a particular asset, including its colour sets, it's name (moniker), and the wallet model that represents it.
class AssetDefinition(object):
    def __init__(self, model, params):
        self.model = model
        self.monikers = params.get('monikers', [])
        self.color_set = ColorSet(model, params.get('color_set'))

    def get_monikers(self):
        return self.monikers

    def get_color_set(self):
        return self.color_set

    def get_utxo_value(self, utxo):
        return utxo.value

    def make_operational_tx_spec(self, tx_spec):
        if (not isinstance(tx_spec, txcons.BasicTxSpec) 
            or not tx_spec.is_monoasset()
            or not tx_spec.is_monocolor()):
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
            if len(self.color_set.color_id_set)>0:
                raise Exception('unable to make transaction constructor for more than one color')
            return txcons.MonocolorTC(self.model, self)

    def get_data(self):
        return {"monikers": self.monikers,
                        "color_set": self.color_set.get_data()}

# Manages asset definitions
class AssetDefinitionManager(object):
    def __init__(self, model, config):
        self.config = config
        self.model = model
        self.asset_definitions = []
        self.assdef_by_moniker = {}
        btcdef = AssetDefinition(model, {"moniker": "bitcoin",
                                                                         "color_set": [""]})
        self.assdef_by_moniker["bitcoin"] = btcdef
        for ad_params in config.get('asset_definitions', []):
            self.register_asset_definition(AssetDefinition(model, ad_params))

    def register_asset_definition(self, assdef):
        self.asset_definitions.append(assdef)
        for moniker in assdef.get_monikers():
            if moniker in self.assdef_by_moniker:
                raise Exception('more than one asset definition have same moniker')
            self.assdef_by_moniker[moniker] = assdef

    def add_asset_definition(self, params):
        assdef = AssetDefinition(self.model, params)
        self.register_asset_definition(assdef)
        self.update_config()
        return assdef

    def get_asset_by_moniker(self, moniker):
        return self.assdef_by_moniker.get(moniker)

    def update_config(self):
        self.config['asset_definitions'] = [assdef.get_data() for assdef in self.asset_definitions]

class AddressRecord(object):
    """data associated with an address: keypair, color_set, ..."""
    def __init__(self, model, params):
        self.model = model
        self.color_set = ColorSet(model, params.get('color_set'))
        if params.get('testnet', False):
            self.meat = meat.TestnetAddress.fromObj(params.get('address_data'))
        else:
            self.meat = meat.Address.fromObj(params.get('address_data'))

    def get_color_set(self):
        return self.color_set

    def get_data(self):
        return {"color_set": self.color_set.get_data(),
                "address_data": self.meat.getJSONData()}

    def get_address(self):
        return self.meat.pubkey

    @classmethod
    def new(cls, model, color_set, testnet=False):
        if testnet:
            newaddr = meat.TestnetAddress.new()
        else:
            newaddr = meat.Address.new()
        return cls(model, {"color_set": color_set.get_data(),
                           "address_data": newaddr.getJSONData(),
                           "testnet": testnet})


class WalletAddressManager(object):
    def __init__(self, model, config):
        self.config = config
        self.testnet = config.get('testnet', False);
        self.model = model
        self.addresses = []
        for addr_params in config.get('addresses', []):
            addr_params['testnet'] = self.testnet
            try:
                address = AddressRecord(model, addr_params)
                self.addresses.append(address)
            except meat.InvalidAddressError:
                address_type = "Bitcoin"
                if self.testnet:
                    address_type = "Testnet"
                #print "%s is an invalid %s address" % (addr_params['address_data']['pubkey'], address_type)

    def get_new_address(self, color_set):
        na = AddressRecord.new(self.model, color_set, self.testnet)
        self.addresses.append(na)
        self.update_config()
        return na

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
        self.config['addresses'] = [addr.get_data() for addr in self.addresses]

class ColoredCoinContext(object):
    def __init__(self, config):

        params = config.get('ccc', {})
        self.testnet = config.get('testnet', False)

        from coloredcoinlib import blockchain
        from coloredcoinlib import builder
        from coloredcoinlib import store
        from coloredcoinlib import colormap
        from coloredcoinlib import colordata

        self.blockchain_state = blockchain.BlockchainState(None, self.testnet)

        self.store_conn = store.DataStoreConnection(params.get("color.db", "color.db"))
        self.cdstore = store.ColorDataStore(self.store_conn.conn)
        self.metastore = store.ColorMetaStore(self.store_conn.conn)

        self.colormap = colormap.ColorMap(self.metastore)

        cdbuilder = builder.ColorDataBuilderManager(self.colormap, self.blockchain_state,
                                                    self.cdstore, self.metastore)

        self.colordata = colordata.ThickColorData(cdbuilder, self.blockchain_state, self.cdstore)



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
        self.address_man = WalletAddressManager(self, config)
        self.coin_query_factory = CoinQueryFactory(self, config)
        self.utxo_man = utxodb.UTXOManager(self, config)
        self.txdb = txdb.TxDb(self, config)
        self.tx_spec_transformer = txcons.TransactionSpecTransformer(self, config)

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
