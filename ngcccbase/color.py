from pycoin.encoding import hash160_sec_to_bitcoin_address

from coloredcoinlib import (BlockchainState, ColorDataBuilderManager,
                            AidedColorDataBuilder, FullScanColorDataBuilder,
                            DataStoreConnection, ColorDataStore,
                            ColorMetaStore, ColorMap,
                            ThinColorData, ThickColorData)
from services.chroma import ChromaBlockchainState
from services.electrum import EnhancedBlockchainState


class ColoredCoinContext(object):
    """Interface to the Colored Coin Library's various offerings.
    Specifically, this object provides access to a storage mechanism
    (store_conn, cdstore, metastore), the color mapping (colormap)
    and color data (Thick Color Data)
    """
    def __init__(self, config):
        """Creates a Colored Coin Context given a config <config>
        """
        params = config.get('ccc', {'thin':True})

        color_data_class = ThickColorData
        color_data_builder = FullScanColorDataBuilder
        blockchain_state_class = BlockchainState
        if params.get('thin'):
            color_data_class = ThinColorData
            color_data_builder = AidedColorDataBuilder
            blockchain_state_class = ChromaBlockchainState

        self.testnet = config.get('testnet', False)
        self.blockchain_state = blockchain_state_class.from_url(
            None, self.testnet)

        if not params.get('thin') and not self.testnet:
            try:
                # try fetching transaction from the second block of
                # the bitcoin blockchain to see whether txindex works
                self.blockchain_state.bitcoind.getrawtransaction(
                    "9b0fc92260312ce44e74ef369f5c66bbb85848f2eddd5"
                    "a7a1cde251e54ccfdd5")
            except Exception as e:
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
            self.metastore, color_data_builder)

        self.colordata = color_data_class(
            cdbuilder, self.blockchain_state, self.cdstore, self.colormap)

    def raw_to_address(self, raw_address):
        return hash160_sec_to_bitcoin_address(raw_address,
                                              is_test=self.testnet)
