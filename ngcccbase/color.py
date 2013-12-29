from pycoin.encoding import hash160_sec_to_bitcoin_address

from coloredcoinlib import (BlockchainState, ColorDataBuilderManager,
                            FullScanColorDataBuilder, DataStoreConnection,
                            ColorDataStore, ColorMetaStore, ColorMap,
                            ThickColorData)
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
        params = config.get('ccc', {})
        self.testnet = config.get('testnet', False)
        self.blockchain_state = BlockchainState.from_url(None, self.testnet)

        if not self.testnet:
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
            self.metastore, FullScanColorDataBuilder)

        self.colordata = ThickColorData(
            cdbuilder, self.blockchain_state, self.cdstore, self.colormap)

    def raw_to_address(self, raw_address):
        return hash160_sec_to_bitcoin_address(raw_address,
                                              is_test=self.testnet)
