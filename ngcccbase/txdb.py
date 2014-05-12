from coloredcoinlib.store import DataStore, DataStoreConnection, PersistentDictStore, unwrap1
from ngcccbase.services.blockchain import BlockchainInfoInterface
from txcons import RawTxSpec
from verifier import Verifier

from time import time
from urllib2 import HTTPError



TX_STATUS_UNKNOWN = 0
TX_STATUS_UNCONFIRMED = 1
TX_STATUS_CONFIRMED = 2
TX_STATUS_INVALID = 3

create_transaction_table = """\
CREATE TABLE tx_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txhash TEXT,
    data TEXT,
    status INTEGER
);
"""

class TxDataStore(DataStore):
    def __init__(self, conn):
        super(TxDataStore, self).__init__(conn)
        if not self.table_exists('tx_data'):
            self.execute(create_transaction_table)
            self.execute(
                "CREATE UNIQUE INDEX tx_data_txhash ON tx_data (txhash)")

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


class BaseTxDb(object):
    def __init__(self, model, config):
        self.model = model
        self.store = TxDataStore(self.model.store_conn.conn)
        self.last_status_check = dict()
        self.recheck_interval = 60

    def purge_tx_db(self):
        self.store.purge_tx_data()

    def get_all_tx_hashes(self):
        return self.store.get_all_tx_hashes()

    def get_tx_by_hash(self, txhash):
        return self.store.get_tx_by_hash(txhash)

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
        self.verifier = Verifier(self.model.get_blockchain_state())
        self.confirmed_txs = set()

    def identify_tx_status(self, txhash):
        if txhash in self.confirmed_txs:
            return TX_STATUS_CONFIRMED
        try:
            verified = self.verifier.verify_merkle(txhash)
        except HTTPError:
            verified = False
        if verified:
            confirmations = self.verifier.get_confirmations(txhash)
            if confirmations == 0:
                return TX_STATUS_UNCONFIRMED
            else:
                self.confirmed_txs.add(txhash)
                return TX_STATUS_CONFIRMED
        else:
            return TX_STATUS_INVALID
