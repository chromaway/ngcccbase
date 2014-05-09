"""
wallet_model.py

Wallet Model: part of Wallet MVC structure

Model provides facilities for working with addresses, coins and asset
definitions, but it doesn't implement high-level operations
(those are implemented in controller).
"""

from collections import defaultdict

from asset import AssetDefinitionManager
from color import ColoredCoinContext
from coloredcoinlib import ColorSet, toposorted
from txdb import NaiveTxDb, TrustingTxDb
from txcons import TransactionSpecTransformer
from coindb import CoinQuery, CoinManager
from utxo_fetcher import SimpleUTXOFetcher
from coloredcoinlib import BlockchainState
from ngcccbase.services.chroma import ChromaBlockchainState
from ngcccbase.services.helloblock import HelloBlockInterface
from txhistory import TxHistory


class CoinQueryFactory(object):
    """Object that creates Queries, which in turn query the UTXO store.
    """
    def __init__(self, model, config):
        """Given a wallet <model> and a config <config>,
        create a query factory.
        """
        self.model = model

    def make_query(self, query):
        """Create a CoinQuery from query <query>. Queries are dicts with:
        color_set - color associated with this query
        """
        query = query.copy()
        color_set = query.get('color_set')
        if not color_set:
            if 'color_id_set' in query:
                color_set = ColorSet.from_color_ids(
                    self.model.get_color_map(), query['color_id_set'])
            elif 'asset' in query:
                color_set = query['asset'].get_color_set()
            else:
                raise Exception('color set is not specified')
        if 'spent' not in query:
            query['spent'] = False
        return CoinQuery(self.model, color_set, query)


class WalletModel(object):
    """Represents a colored-coin wallet
    """
    def __init__(self, config, store_conn):
        """Creates a new wallet given a configuration <config>
        """
        self.store_conn = store_conn  # hackish!
        self.testnet = config.get('testnet', False)
        self.init_blockchain_state(config)
        self.init_tx_db(config)
        self.init_utxo_fetcher(config)
        self.ccc = ColoredCoinContext(config, 
                                      self.blockchain_state)
        self.ass_def_man = AssetDefinitionManager(self.ccc.colormap, config)
        self.init_wallet_address_manager(config)
        self.coin_query_factory = CoinQueryFactory(self, config)
        self.coin_man = CoinManager(self, config)
        self.tx_spec_transformer = TransactionSpecTransformer(self, config)
        self.tx_history = TxHistory(self)

    def init_wallet_address_manager(self, config):
        if config.get('bip0032'):
            from bip0032 import HDWalletAddressManager
            self.address_man = HDWalletAddressManager(self.ccc.colormap, config)
        else:
            from deterministic import DWalletAddressManager
            self.address_man = DWalletAddressManager(self.ccc.colormap, config)
            
    def init_tx_db(self, config):
        if self.testnet:
            self.txdb = NaiveTxDb(self, config)
        else:
            hb_interface = HelloBlockInterface(self.testnet)
            self.txdb = TrustingTxDb(self, config,
                                     hb_interface.get_tx_confirmations)

    def init_utxo_fetcher(self, config):
        self.utxo_fetcher = SimpleUTXOFetcher(
            self, config.get('utxo_fetcher', {}))

    def init_blockchain_state(self, config):
        thin = config.get('thin', True)
        if thin and not config.get('use_bitcoind', False):
            chromanode_url = config.get('chromanode_url', None)
            if not chromanode_url:
                if self.testnet:
                    chromanode_url = "http://chromanode-tn.bitcontracts.org"
                else:
                    chromanode_url = "http://chromanode.bitcontracts.org"
            self.blockchain_state = ChromaBlockchainState(
                chromanode_url,
                self.testnet)
        else:
            self.blockchain_state = BlockchainState.from_url(
                None, self.testnet)

        if not thin and not self.testnet:
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

    def get_blockchain_state(self):
        return self.blockchain_state

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

    def get_coin_manager(self):
        """Access method for coin manager
        """
        return self.coin_man

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

    def get_coin_manager(self):
        return self.coin_man

    def get_color_map(self):
        """Access method for ColoredCoinContext's colormap
        """
        return self.ccc.colormap

    def get_color_def(self, color):
        return self.ccc.colormap.get_color_def(color)
