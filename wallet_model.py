# Wallet Model: part of Wallet MVC structure

# model provides facilities for working with addresses, coins and asset definitions,
# but it doesn't implement high-level operations (those are implemented in controller)

class ColorSet(object):
    """a set of colors which belong to certain asset, 
    it can be used to filter addresses and UTXOs"""
    def __init__(self, model, color_desc_list):
        self.color_desc_list = color_desc_list
        self.color_id_set = set()
        colormap = model.get_color_map()
        for color_desc in color_desc_list:
            self.color_id_set.add(colormap.resolve_color_desc(color_desc))
    def getData(self):
        return self.color_desc_list
    def has_color_id(self, color_id):
        return (color_id in self.color_id_set)
    def intersects(self, other):
        return len(self.color_id_set & other.color_id_set) > 0

class AssetDefinition(object):
    def __init__(self, model, params):
        self.moniker = params.get('moniker')
        self.color_set = ColorSet(model, params.get('color_set'))
    def get_moniker(self):
        return self.moniker
    def get_color_set(self):
        return self.color_set
    def get_utxo_value(self):
        pass

class AssetDefinitionManager(object):
    """manages asset definitions"""
    def __init__(self, model, config):
        self.asset_definitions = []
        self.assdef_by_moniker = {}
        btcdef = AssetDefinition(model, {"moniker": "bitcoin",
                                         "color_set": [""]})
        self.assdef_by_moniker["bitcoin"] = btcdef        
        for ad_params in config.get('asset_definitions', []):
            assdef = AssetDefinition(model, ad_params)
            asset_definitions.append(assdef)
            moniker = assdef.get_moniker()
            if moniker:
                if moniker in assdef_by_moniker:
                    raise Exception('more than one asset definition have same moniker')
                self.assdef_by_moniker[moniker] = assdef
    def get_asset_by_moniker(self, moniker):
        return self.assdef_by_moniker.get(moniker)

class AddressWrapper(object):
    def __init__(self, model, params):
        import meat

        self.color_set = ColorSet(model, params.get('color_set'))
        self.meat = meat.Address.fromObj(params.get('address_data'))
    def get_color_set(self):
        return self.color_set
    def getData(self):
        return {"color_set": self.color_set.getData(),
                "address_data": self.meat.getJSONData()}
    def get_address(self):
        return self.meat.pubkey
    @classmethod
    def new(cls, model, color_set):
        import meat
        newaddr = meat.Address.new()
        return cls(model, {"color_set": color_set.getData(),
                           "address_data": newaddr.getJSONData()})

class WalletAddressManager(object):
    def __init__(self, model, config):
        self.config = config
        self.model = model
        self.addresses = []
        for addr_params in config.get('addresses', []):
            address = AddressWrapper(model, addr_params)
            self.addresses.append(address)

    def get_new_address(self, color_set):
        na = AddressWrapper.new(self.model, color_set)
        self.addresses.append(na)
        self.update_config()
        return na

    def get_addresses_for_color_set(self, color_set):
        return [addr for addr in self.addresses 
                if color_set.intersects(address.get_color_set())]

    def update_config(self):
        self.config['addresses'] = [addr.getData() for addr in self.addresses]

class ColoredCoinContext(object):
    def __init__(self, config):

        params = config.get('ccc')

        from coloredcoinlib import agent
        from coloredcoinlib import blockchain
        from coloredcoinlib import builder
        from coloredcoinlib import colordef
        from coloredcoinlib import store
        from coloredcoinlib import colormap

        self.blockchain_state = blockchain.BlockchainState(params.get('bitcoind_url'))
        
        self.store_conn = store.DataStoreConnection(params.get("color.db", "color.db"))
        self.cdstore = store.ColorDataStore(self.store_conn.conn)
        self.metastore = store.ColorMetaStore(self.store_conn.conn)

        self.colormap = colormap.ColorMap(self.metastore)


class CoinQuery(object):
    """can be used to request UTXOs satisfying certain criteria"""
    def __init__(self, model, asset):
        self.model = model
        self.asset = asset
    def get_result(self):
        addr_man = self.model.get_address_manager()
        color_set = self.asset.get_color_set()
        addresses = addr_man.get_addresses_for_color_set(color_set)
        utxos = []
        for address in addresses:
            utxos.extend(address.getUTXOs(color_set))
        return utxos

class CoinQueryFactory(object):
    def __init__(self, model, config):
        self.model = model
    def make_query(self, query):
        return CoinQuery(self.model, query.get("asset"))

class WalletModel(object):
    def __init__(self, config):
        self.ccc = ColoredCoinContext(config)
        self.ass_def_man = AssetDefinitionManager(self, config)
        self.address_man = WalletAddressManager(self, config)
        self.coin_query_factory = CoinQueryFactory(self, config)
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


