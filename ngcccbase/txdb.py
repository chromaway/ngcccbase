from time import time
from urllib2 import HTTPError
import threading
import os

from pycoin.encoding import double_sha256

from coloredcoinlib.store import DataStore, DataStoreConnection, PersistentDictStore, unwrap1
from ngcccbase.services.blockchain import BlockchainInfoInterface
from txcons import RawTxSpec
from blockchain import VerifiedBlockchainState



TX_STATUS_UNKNOWN = 0
TX_STATUS_UNCONFIRMED = 1
TX_STATUS_CONFIRMED = 2
TX_STATUS_INVALID = 3

create_transaction_table = """\
CREATE TABLE tx_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txhash TEXT,
    data TEXT,
    status INTEGER,
    block_height INTEGER
);
"""

class TxDataStore(DataStore):
    def __init__(self, conn):
        super(TxDataStore, self).__init__(conn)
        if not self.table_exists('tx_data'):
            self.execute(create_transaction_table)
            self.execute(
                "CREATE UNIQUE INDEX tx_data_txhash ON tx_data (txhash)")
        if not self.column_exists('tx_data', 'block_height'):
            self.execute(
                "ALTER TABLE tx_data ADD COLUMN block_height INTEGER")

    def purge_tx_data(self):
        self.execute("DELETE FROM tx_data")

    def add_tx(self, txhash, txdata, status=TX_STATUS_UNKNOWN):
        return self.execute(
            "INSERT INTO tx_data (txhash, data, status) VALUES (?, ?, ?)",
            (txhash, txdata, status))

    def set_tx_status(self, txhash, status):
        self.execute("UPDATE tx_data SET status = ? WHERE txhash = ?",
                     (status, txhash))
    
    def get_tx_status(self, txhash):
        return unwrap1(self.execute("SELECT status FROM tx_data WHERE txhash = ?",
                                    (txhash, )).fetchone())

    def get_tx_by_hash(self, txhash):
        return self.execute("SELECT * FROM tx_data WHERE txhash = ?",
                            (txhash, )).fetchone()

    def get_all_tx_hashes(self):
        return map(unwrap1,
                   self.execute("SELECT txhash FROM tx_data").fetchall())

    def set_block_height(self, txhash, height):
        self.execute("UPDATE tx_data SET block_height = ? WHERE txhash = ?",
                     (height, txhash))

    def reset_from_height(self, height):
        self.execute("UPDATE tx_data SET status = 0 \
WHERE (block_height >= ?) OR (block_height IS NULL)",
                     (height,))

class BaseTxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.store_conn.conn)
        self.last_status_check = dict()
        self.recheck_interval = 60
        self.bs = self.model.get_blockchain_state()

    def purge_tx_db(self):
        self.store.purge_tx_data()

    def get_all_tx_hashes(self):
        return self.store.get_all_tx_hashes()

    def get_tx_by_hash(self, txhash):
        return self.store.get_tx_by_hash(txhash)

    def update_tx_block_height(self, txhash, status):
        if status == TX_STATUS_CONFIRMED:
            try:
                block_hash, _ = self.bs.get_tx_blockhash(txhash)
                height = self.bs.get_block_height(block_hash)
            except:
                return
            self.store.set_block_height(txhash, height)

    def add_raw_tx(self, raw_tx, status=TX_STATUS_UNCONFIRMED):
        return self.add_tx(raw_tx.get_hex_txhash(),
                           raw_tx.get_hex_tx_data(),
                           raw_tx,
                           status)

    def add_tx_by_hash(self, txhash, status=None):
        bs = self.model.get_blockchain_state()
        txdata = bs.get_raw(txhash)
        raw_tx = RawTxSpec.from_tx_data(self.model,
                                        txdata.decode('hex'))
        return self.add_tx(txhash, txdata, raw_tx, status)

    def add_tx(self, txhash, txdata, raw_tx, status=None):
        if not self.store.get_tx_by_hash(txhash):
            if not status:
                status = self.identify_tx_status(txhash)
            self.store.add_tx(txhash, txdata, status)
            self.update_tx_block_height(txhash, status)
            self.last_status_check[txhash] = time()
            self.model.get_coin_manager().apply_tx(txhash, raw_tx)
            return True
        else:
            old_status = self.store.get_tx_status(txhash)
            new_status = self.maybe_recheck_tx_status(txhash, old_status)
            return old_status != new_status

    def recheck_tx_status(self, txhash):
        status = self.identify_tx_status(txhash)
        self.store.set_tx_status(txhash, status)
        self.update_tx_block_height(txhash, status)
        return status
   
    def maybe_recheck_tx_status(self, txhash, status):
        if status == TX_STATUS_CONFIRMED:
            # do not recheck those which are already confirmed
            return status
        if (time() - self.last_status_check.get(txhash, 0)) < self.recheck_interval:
            return status
        status = self.recheck_tx_status(txhash)
        self.last_status_check[txhash] = time()
        return status

    def is_tx_valid(self, txhash):
        status = self.store.get_tx_status(txhash)
        if status == TX_STATUS_CONFIRMED:
            return True
        status = self.maybe_recheck_tx_status(txhash, status)
        return status != TX_STATUS_INVALID

    def is_tx_confirmed(self, txhash):
        status = self.store.get_tx_status(txhash)
        if status != TX_STATUS_CONFIRMED:
            status = self.maybe_recheck_tx_status(txhash, status)
        return status == TX_STATUS_CONFIRMED


class NaiveTxDb(BaseTxDb):
    """Native TxDb trusts results of get_blockchain_state"""
    def identify_tx_status(self, txhash):
        block_hash, in_mempool = self.model.get_blockchain_state().\
            get_tx_blockhash(txhash)
        if block_hash:
            return TX_STATUS_CONFIRMED
        elif in_mempool:
            return TX_STATUS_UNCONFIRMED
        else:
            return TX_STATUS_INVALID


class TrustingTxDb(BaseTxDb):
    """TxDb which trusts confirmation data it gets from an external source"""
    
    def __init__(self, model, config, get_tx_confirmations):
        super(TrustingTxDb, self).__init__(model, config)
        self.confirmed_txs = set()
        self.get_tx_confirmations = get_tx_confirmations

    def identify_tx_status(self, txhash):
        if txhash in self.confirmed_txs:
            return TX_STATUS_CONFIRMED
        confirmations = self.get_tx_confirmations(txhash)
        if confirmations > 0:
            self.confirmed_txs.add(txhash)
            return TX_STATUS_CONFIRMED
        elif confirmations == 0:
            return TX_STATUS_UNCONFIRMED
        else:
            # check if BlockchainState is aware of it
            block_hash, in_mempool = self.model.get_blockchain_state().\
                get_tx_blockhash(txhash)
            if block_hash or in_mempool:
                return TX_STATUS_UNCONFIRMED
            else:
                return TX_STATUS_INVALID


class VerifiedTxDb(BaseTxDb):
    def __init__(self, model, config):
        super(VerifiedTxDb, self).__init__(model, config)
        self.bs = self.model.get_blockchain_state()
        self.vbs = VerifiedBlockchainState(
            self.bs,
            self,
            config.get('testnet', False),
            os.path.dirname(self.model.store_conn.path)
        )
        self.vbs.start()
        self.lock = threading.Lock()
        self.verified_tx = {}

    def __del__(self):
        if self.vbs:
            self.vbs.stop()

    def _get_merkle_root(self, merkle_s, start_hash, pos):
        hash_decode = lambda x: x.decode('hex')[::-1]
        hash_encode = lambda x: x[::-1].encode('hex')

        h = hash_decode(start_hash)
        # i is the "level" or depth of the binary merkle tree.
        # item is the complementary hash on the merkle tree at this level
        for i, item in enumerate(merkle_s):
            # figure out if it's the left item or right item at this level
            if pos >> i & 1:
                # right item (odd at this level)
                h = double_sha256(hash_decode(item) + h)
            else:
                # left item (even at this level)
                h = double_sha256(h + hash_decode(item))
        return hash_encode(h)

    def _verify_merkle(self, txhash):
        result = self.bs.get_merkle(txhash)
        merkle, tx_height, pos = result.get('merkle'), \
            result.get('block_height'), result.get('pos')

        merkle_root = self._get_merkle_root(merkle, txhash, pos)
        header = self.vbs.get_header(tx_height)
        if header is None:
            return False
        if header.get('merkle_root') != merkle_root:
            return False

        with self.lock:
            self.verified_tx[txhash] = tx_height
        return True

    def update_tx_block_height(self, txhash, status):
        with self.lock:
            if txhash in self.verified_tx:
                self.store.set_block_height(txhash,
                                            self.verified_tx[txhash])

    def drop_from_height(self, height):
        with self.lock:
            self.verified_tx = {key: value for key, value in self.verified_tx.items() if value < height}

    def get_confirmations(self, txhash):
        with self.lock:
            if txhash in self.verified_tx:
                height = self.verified_tx[txhash]
                return self.vbs.height - height + 1
            else:
                return None

    def identify_tx_status(self, txhash):
        block_hash, in_mempool = self.bs.get_tx_blockhash(txhash)
        if (not block_hash) and (not in_mempool):
            return TX_STATUS_INVALID
        if not block_hash:
            return TX_STATUS_UNCONFIRMED
        confirmations = self.get_confirmations(txhash)
        if confirmations is None:
            verified = self._verify_merkle(txhash)
            if verified:
                return self.identify_tx_status(txhash)
            else:
                return TX_STATUS_UNCONFIRMED
        if confirmations == 0:
            return TX_STATUS_UNCONFIRMED
        return TX_STATUS_CONFIRMED
