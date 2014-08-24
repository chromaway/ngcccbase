from pycoin.encoding import hash160_sec_to_bitcoin_address

from coloredcoinlib import (ColorDataBuilderManager,
                            AidedColorDataBuilder, 
                            FullScanColorDataBuilder, DataStoreConnection,
                            ColorDataStore, ColorMetaStore, ColorMap,
                            ThickColorData, ThinColorData)
from services.electrum import EnhancedBlockchainState


class ColoredCoinContext(object):
    """Interface to the Colored Coin Library's various offerings.
    Specifically, this object provides access to a storage mechanism
    (store_conn, cdstore, metastore), the color mapping (colormap)
    and color data (Thick Color Data)
    """
    def __init__(self, config, blockchain_state):
        """Creates a Colored Coin Context given a config <config>
        """
        params = config.get('ccc', {})
        self.blockchain_state = blockchain_state
        self.testnet = config.get('testnet', False)
        thin = config.get('thin', True)

        if thin:
            color_data_class = ThinColorData
            color_data_builder = AidedColorDataBuilder
        else:
            color_data_class = ThickColorData
            color_data_builder = FullScanColorDataBuilder
            
        self.store_conn = DataStoreConnection(
            params.get("colordb_path", "color.db"))
        self.cdstore = ColorDataStore(self.store_conn.conn)
        self.metastore = ColorMetaStore(self.store_conn.conn)
        self.colormap = ColorMap(self.metastore)
        
        cdbuilder = ColorDataBuilderManager(
            self.colormap, self.blockchain_state, self.cdstore,
            self.metastore, color_data_builder)

        self.colordata = color_data_class(
            cdbuilder, self.blockchain_state, self.cdstore, self.colormap)

    def raw_to_address(self, raw_address):
        prefix = self.testnet and b'\x6f' or b"\0"
        return hash160_sec_to_bitcoin_address(raw_address,
                                              address_prefix=prefix)

